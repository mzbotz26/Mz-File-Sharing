# © MzBotz Premium File Store Bot

import asyncio, time, random, string, re
from plugins.cbb import start_buttons
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import *
from helper_func import (
    subscribed,
    encode,
    decode,
    get_messages,
    get_shortlink,
    get_verify_status,
    update_verify_status,
    get_exp_time
)

from database.database import (
    add_user, del_user, full_userbase, present_user,
    get_premium, set_premium, remove_premium
)

WAIT_MSG = "<b>Working...</b>"

# ================= USER FILE CAPTION =================

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

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    user_id=message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status=await get_verify_status(user_id)
    premium=await get_premium(user_id)

    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time()-verify_status['verified_time']):
        await update_verify_status(user_id,is_verified=False)

    # ---------- VERIFY TOKEN ----------
    if message.text.startswith("/start verify_"):
        token=message.text.split("_",1)[1]
        if verify_status['verify_token']!=token:
            return await message.reply("❌ Invalid or expired token.")
        await update_verify_status(user_id,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verification successful. Now open file again.")

    # ---------- FILE FETCH ----------
    if len(message.command)>1:

        if not (premium["is_premium"] and time.time()<premium["premium_expiry"]):
            if IS_VERIFY and not verify_status['is_verified']:
                return await send_verify(client,message,user_id)

        base64_string=message.command[1]

        try:
            decoded=await decode(base64_string)
            arg=decoded.split("-")
        except:
            return await message.reply("❌ Invalid link.")

        if len(arg)==2:
            ids=[int(int(arg[1])/abs(client.db_channel.id))]
        elif len(arg)==3:
            start=int(int(arg[1])/abs(client.db_channel.id))
            end=int(int(arg[2])/abs(client.db_channel.id))
            ids=range(start,end+1)
        else:
            return await message.reply("❌ Invalid link.")

        temp=await message.reply("📤 Fetching your file...")

        try:
            messages=await get_messages(client,ids)
        except:
            return await temp.edit("❌ File not found.")

        await temp.delete()
        sent=[]

        for msg in messages:
            try:
                caption=build_user_caption(msg,premium["is_premium"])
                s=await msg.copy(
                    chat_id=message.chat.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    protect_content=PROTECT_CONTENT
                )
                sent.append(s)
                await asyncio.sleep(0.4)
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except:
                pass

        note=await message.reply("⚠ Files auto delete after 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        try: await note.delete()
        except: pass
        return

    # ---------- NORMAL START ----------

    status_text="✅ Verified" if verify_status['is_verified'] else "❌ Not Verified"
    expire_text="∞" if verify_status['is_verified'] else get_exp_time(VERIFY_EXPIRE)

    premium_text="👑 Premium Active" if premium["is_premium"] and time.time()<premium["premium_expiry"] else "❌ Not Premium"

    text=f"""ʜᴇʟʟᴏ {message.from_user.mention}

━━━━━━━━━━━━━━
🔐 Verification : {status_text}
👑 Premium : {premium_text}
⏳ Expiry : {expire_text}
━━━━━━━━━━━━━━
"""

    if START_PIC:
        await client.send_photo(
            message.chat.id,START_PIC,
            caption=text,
            reply_markup=start_buttons(),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(text,reply_markup=start_buttons())

# ================= VERIFY =================

async def send_verify(client,message,user_id):

    token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
    await update_verify_status(user_id,verify_token=token,is_verified=False)

    link=await get_shortlink(
        SHORTLINK_URL,SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("Verify Now",url=link)],
        [InlineKeyboardButton("How To Use",url=TUT_VID)]
    ])

    await message.reply("🔐 Verification Required",reply_markup=btn)

# ================= PREMIUM =================

@Bot.on_message(filters.command("premium") & filters.private)
async def premium_cmd(client,message):
    btn=InlineKeyboardMarkup([
        [InlineKeyboardButton("Buy Premium",callback_data="buy_premium")]
    ])
    await message.reply("👑 Premium Plans\n\n7 Days ₹49\n30 Days ₹149",reply_markup=btn)

@Bot.on_callback_query(filters.regex("buy_premium"))
async def buy_premium(client,query):
    u=query.from_user
    await client.send_message(OWNER_ID,f"💰 Premium Request\nUser: {u.mention}\nID: {u.id}")
    await query.message.edit("✅ Owner notified. Wait for instructions.")

@Bot.on_message(filters.command("addpremium") & filters.private & filters.user(ADMINS))
async def add_premium_cmd(client,message):
    uid=int(message.command[1])
    days=int(message.command[2])
    await set_premium(uid,days)
    await message.reply("Premium added.")
    await client.send_message(uid,f"👑 Premium activated for {days} days.")

@Bot.on_message(filters.command("removepremium") & filters.private & filters.user(ADMINS))
async def remove_premium_cmd(client,message):
    uid=int(message.command[1])
    await remove_premium(uid)
    await message.reply("Premium removed.")
