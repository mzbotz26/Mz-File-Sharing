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

WAIT_MSG = "<b>Working...</b>"

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

# ================= REFERRAL HANDLER =================

async def handle_referral(client, uid, ref_id):

    if uid == ref_id:
        return

    ref_status = await get_verify_status(ref_id)

    count = ref_status.get("referrals",0) + 1
    await update_verify_status(ref_id, referrals=count)

    # Notify referrer
    try:
        await client.send_message(
            ref_id,
            f"🎉 New Referral Joined!\n\nTotal Referrals: {count}/5"
        )
    except:
        pass

    # Auto premium after 5 referrals
    if count == 5:
        expire = int(time.time()) + 3*86400
        await add_premium(ref_id, expire)

        await update_verify_status(ref_id, referrals=0)

        try:
            await client.send_message(
                ref_id,
                "👑 Congratulations!\n\nYou earned 3 Days Premium from referrals 🎁"
            )
        except:
            pass

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    uid = message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    # -------- Referral Detect --------
    if len(message.command)>1 and message.command[1].startswith("ref_"):
        ref_id = int(message.command[1].split("_")[1])
        await handle_referral(client, uid, ref_id)

    verify = await get_verify_status(uid)
    premium = await get_premium(uid)

    # -------- Verify Expiry --------
    if verify["is_verified"] and verify_expired(verify):
        await update_verify_status(uid,is_verified=False)

    # -------- Premium Expiry Reminder --------
    if premium and premium["expire_time"]:
        left = premium["expire_time"] - time.time()
        if 0 < left < 86400:
            await client.send_message(uid,"⏰ Your premium will expire within 24 hours.")
        if left <= 0:
            await remove_premium(uid)
            await client.send_message(uid,"⚠️ Your premium has expired.")

    # -------- Verify Token --------
    if message.text.startswith("/start verify_"):
        token = message.text.split("_",1)[1]
        if verify["verify_token"] != token:
            return await message.reply("❌ Invalid token.")
        await update_verify_status(uid,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verification completed. Open file again.")

    # -------- FILE FETCH --------
    if len(message.command) > 1 and not message.command[1].startswith("ref_"):

        if not premium or (premium and premium["expire_time"] and time.time()>premium["expire_time"]):
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
                cap=build_user_caption(m, premium and premium["is_premium"])
                s=await m.copy(
                    chat_id=uid,
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                    protect_content=PROTECT_CONTENT
                )
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

    # -------- NORMAL START --------

    vtxt="✅ Verified" if verify["is_verified"] else "❌ Not Verified"
    ptxt="👑 Premium" if premium and premium["is_premium"] else "❌ Not Premium"
    ref_count = verify.get("referrals",0)

    ref_link = f"https://t.me/{client.username}?start=ref_{uid}"

    text=f"""ʜᴇʟʟᴏ {message.from_user.mention}

━━━━━━━━━━━━━━
🔐 Verification : {vtxt}
👑 Premium : {ptxt}
👥 Referrals : {ref_count}/5
━━━━━━━━━━━━━━

🎁 Invite friends & get free premium:
{ref_link}
"""

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Premium Plans", callback_data="premium")],
        [InlineKeyboardButton("🎁 Referral Info", callback_data="refinfo")]
    ])

    await message.reply(text, reply_markup=btn)

# ================= SEND VERIFY =================

async def send_verify(client,message,uid):

    token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
    await update_verify_status(uid, verify_token=token, is_verified=False)

    link=await get_shortlink(
        SHORTLINK_URL,SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("Verify Now",url=link)],
        [InlineKeyboardButton("How To Use",url=VERIFY_TUT_1)]
    ])

    await message.reply("🔐 Verification Required",reply_markup=btn)

# ================= CALLBACKS =================

@Bot.on_callback_query(filters.regex("premium"))
async def premium_cb(client,query):
    await query.message.edit(
        "👑 Premium Plans\n\n7 Days ₹49\n30 Days ₹149\n\nContact Owner for payment."
    )

@Bot.on_callback_query(filters.regex("refinfo"))
async def refinfo_cb(client,query):
    await query.message.edit(
        "🎁 Referral System\n\nInvite 5 users → Get 3 Days Premium Free"
    )

# ================= ADMIN =================

@Bot.on_message(filters.command("users") & filters.user(ADMINS))
async def users(client,message):
    u=await full_userbase()
    await message.reply(f"👥 Total Users: {len(u)}")
