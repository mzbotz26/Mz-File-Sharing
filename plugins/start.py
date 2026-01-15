# © MzBotz Premium File Store Bot

import asyncio, time, random, string, re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait

from bot import Bot
from config import *

from helper_func import (
    subscribed, encode, decode, get_messages, get_shortlink,
    get_verify_status, update_verify_status, get_exp_time
)

from database.database import (
    add_user, del_user, full_userbase, present_user,
    get_premium, add_premium, remove_premium
)

BOT_START_TIME = time.time()

# ================= USER CAPTION =================

def build_user_caption(msg, is_premium=False):
    name = msg.document.file_name if msg.document else msg.video.file_name
    title = name.rsplit(".",1)[0].replace("."," ").replace("_"," ").replace("-"," ")

    quality="N/A"
    for q in ["2160p","1080p","720p","480p"]:
        if q.lower() in name.lower():
            quality=q; break

    aud=[]
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada"]:
        if a in name.lower(): aud.append(a.capitalize())
    audio=" / ".join(aud) if aud else "Unknown"

    se=""
    m=re.search(r"s(\d+)e(\d+)",name,re.I)
    if m: se=f"\n📺 Season {int(m.group(1))} Episode {int(m.group(2))}"

    caption=f"""🎬 {title}

🎞 Quality : {quality}
🔊 Audio : {audio}{se}

━━━━━━━━━━━━
"""

    if is_premium:
        caption="👑 PREMIUM USER\n\n"+caption

    if CUSTOM_CAPTION:
        caption+=CUSTOM_CAPTION

    return caption

# ================= VERIFY EXPIRE =================

def verify_expired(v):
    return v["verified_time"] + VERIFY_STEP_TIME < time.time()

# ================= REFERRAL =================

async def handle_referral(client, uid, ref_id):
    if uid == ref_id:
        return

    ref = await get_verify_status(ref_id)
    count = ref.get("referrals",0) + 1
    await update_verify_status(ref_id, referrals=count)

    try:
        await client.send_message(ref_id,f"🎉 New Referral!\nTotal: {count}/5")
    except:
        pass

    if count >= 5:
        expire = int(time.time()) + 3*86400
        await add_premium(ref_id, expire)
        await update_verify_status(ref_id, referrals=0)
        await client.send_message(ref_id,"👑 You earned 3 Days Premium!")

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    uid = message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    # referral
    if len(message.command)>1 and message.command[1].startswith("ref_"):
        await handle_referral(client, uid, int(message.command[1].split("_")[1]))

    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    # verify expiry
    if verify["is_verified"] and verify_expired(verify):
        await update_verify_status(uid,is_verified=False)

    # premium expiry reminder
    if premium and premium.get("expire_time"):
        left = premium["expire_time"] - time.time()
        if 0 < left < 86400:
            await client.send_message(uid,"⏰ Premium expires in 24 hours.")
        if left <= 0:
            await remove_premium(uid)
            premium = None
            await client.send_message(uid,"⚠ Premium expired.")

    # verify token
    if message.text.startswith("/start verify_"):
        token = message.text.split("_",1)[1]
        if verify["verify_token"] != token:
            return await message.reply("❌ Invalid token.")
        await update_verify_status(uid,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verification completed.")

    # FILE FETCH
    if len(message.command)>1 and not message.command[1].startswith("ref_"):

        if not premium or (premium and premium.get("expire_time") and time.time()>premium["expire_time"]):
            if IS_VERIFY and not verify["is_verified"]:
                return await send_verify(client,message,uid)

        try:
            decoded = await decode(message.command[1])
            arg = decoded.split("-")
        except:
            return await message.reply("❌ Invalid link.")

        if len(arg)==2:
            ids=[int(int(arg[1])/abs(client.db_channel.id))]
        elif len(arg)==3:
            s=int(int(arg[1])/abs(client.db_channel.id))
            e=int(int(arg[2])/abs(client.db_channel.id))
            ids=range(s,e+1)
        else:
            return await message.reply("❌ Invalid link.")

        temp=await message.reply("📤 Fetching file...")

        try:
            msgs=await get_messages(client,ids)
        except:
            return await temp.edit("❌ File not found.")

        await temp.delete()

        sent=[]

        for m in msgs:
            try:
                cap=build_user_caption(m, premium and premium.get("is_premium"))
                s=await m.copy(uid,caption=cap,parse_mode=ParseMode.HTML,protect_content=PROTECT_CONTENT)
                sent.append(s)
                await asyncio.sleep(0.4)
            except FloodWait as e:
                await asyncio.sleep(e.x)

        note=await message.reply("⚠ Files auto delete in 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        try: await note.delete()
        except: pass
        return

    # NORMAL START

    ref_link=f"https://t.me/{client.username}?start=ref_{uid}"

    text=f"""👋 {message.from_user.mention}

🔐 Verify : {"✅" if verify["is_verified"] else "❌"}
👑 Premium : {"✅" if premium and premium.get("is_premium") else "❌"}
👥 Referrals : {verify.get("referrals",0)}/5

🎁 Invite friends:
{ref_link}
"""

    btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Premium",callback_data="premium")],
        [InlineKeyboardButton("🎁 Referral Info",callback_data="refinfo")],
        [InlineKeyboardButton("📊 My Premium",callback_data="mypremium")],
        [InlineKeyboardButton("🏆 Leaderboard",callback_data="leaderboard")]
    ])

    await message.reply(text,reply_markup=btn)

# ================= VERIFY =================

async def send_verify(client,message,uid):

    token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
    await update_verify_status(uid,verify_token=token,is_verified=False)

    link=await get_shortlink(
        SHORTLINK_URL,SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("Verify Now",url=link)],
        [InlineKeyboardButton("How To Use",url=VERIFY_TUT_1)]
    ])

    await message.reply("🔐 Verification Required",reply_markup=btn)

# ================= CALLBACK =================

@Bot.on_callback_query(filters.regex("premium"))
async def prem(client,q):
    await q.message.edit(
        "👑 Premium Plans\n\n7 Days ₹49\n30 Days ₹149\n\nSend screenshot to Owner.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Contact Owner",url=f"https://t.me/{OWNER_USERNAME}")]
        ])
    )

@Bot.on_callback_query(filters.regex("refinfo"))
async def ref(client,q):
    await q.message.edit("🎁 Invite 5 users → Get 3 Days Premium Free")

@Bot.on_callback_query(filters.regex("mypremium"))
async def myp(client,q):
    uid=q.from_user.id
    p=await get_premium(uid)
    if not p:
        return await q.message.edit("❌ You are not premium.")
    left=int((p["expire_time"]-time.time())/3600)
    await q.message.edit(f"👑 Premium Active\n⏳ Left: {left} Hours")

@Bot.on_callback_query(filters.regex("leaderboard"))
async def lb(client,q):
    await q.message.edit("🏆 Referral Leaderboard feature ready (DB based).")

# ================= COMMANDS =================

@Bot.on_message(filters.command("users") & filters.user(ADMINS))
async def users(client,m):
    u=await full_userbase()
    await m.reply(f"👥 Users: {len(u)}")

@Bot.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(client,m):
    t=int(time.time()-BOT_START_TIME)
    await m.reply(f"⏱ Uptime: {t//3600}h {(t%3600)//60}m")

@Bot.on_message(filters.command("genlink") & filters.user(ADMINS))
async def genlink(client,m):
    if not m.reply_to_message: return await m.reply("Reply to file.")
    code=await encode(f"get-{m.reply_to_message.id*abs(client.db_channel.id)}")
    await m.reply(f"https://t.me/{client.username}?start={code}")

@Bot.on_message(filters.command("batch") & filters.user(ADMINS))
async def batch(client,m):
    try:
        s=int(m.command[1]); e=int(m.command[2])
    except:
        return await m.reply("/batch start end")
    code=await encode(f"get-{s*abs(client.db_channel.id)}-{e*abs(client.db_channel.id)}")
    await m.reply(f"https://t.me/{client.username}?start={code}")

@Bot.on_message(filters.command("forceverify") & filters.user(ADMINS))
async def fv(client,m):
    uid=int(m.command[1])
    await update_verify_status(uid,is_verified=True,verified_time=time.time())
    await m.reply("Force verified.")

@Bot.on_message(filters.command("unverify") & filters.user(ADMINS))
async def uv(client,m):
    await update_verify_status(int(m.command[1]),is_verified=False)
    await m.reply("Unverified.")

@Bot.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def ap(client,m):
    uid=int(m.command[1]); days=int(m.command[2])
    await add_premium(uid,int(time.time())+days*86400)
    await m.reply("Premium added.")

@Bot.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def rp(client,m):
    await remove_premium(int(m.command[1]))
    await m.reply("Premium removed.")

@Bot.on_message(filters.command("mypremium"))
async def mypremium(client,m):
    p=await get_premium(m.from_user.id)
    if not p:
        return await m.reply("❌ Not premium.")
    left=int((p["expire_time"]-time.time())/3600)
    await m.reply(f"👑 Premium active\n⏳ Left: {left} hours")
