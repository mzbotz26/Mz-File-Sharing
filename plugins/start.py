# © MzBotz

import asyncio, time, random, string, re
from datetime import datetime, timedelta

from plugins.cbb import start_buttons
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import *
from helper_func import (
    subscribed, encode, decode, get_messages,
    get_shortlink, get_verify_status, update_verify_status, get_exp_time
)
from database.database import (
    add_user, del_user, full_userbase, present_user,
    get_premium, add_premium, remove_premium
)

WAIT_MSG = "<b>Working...</b>"

# ================= TIME PARSER =================

def parse_time(arg):
    arg = arg.lower()
    if arg == "permanent":
        return None

    if "-" in arg:
        return datetime.strptime(arg, "%Y-%m-%d")

    num = int(arg[:-1])
    unit = arg[-1]

    if unit == "h":
        return datetime.utcnow() + timedelta(hours=num)
    if unit == "d":
        return datetime.utcnow() + timedelta(days=num)
    if unit == "m":
        return datetime.utcnow() + timedelta(days=num*30)
    if unit == "y":
        return datetime.utcnow() + timedelta(days=num*365)

    return None

# ================= CLEAN USER CAPTION =================

def build_user_caption(msg, premium=False):
    name = msg.document.file_name if msg.document else msg.video.file_name
    title = name.rsplit(".",1)[0]

    title = title.replace(".", " ").replace("_"," ").replace("-"," ")
    title = re.sub(r"\b(19|20)\d{2}\b","",title)
    title = re.sub(r"\b(2160p|1080p|720p|480p|x264|x265|hevc|hdrip|webdl|bluray|brrip|hdts|cam|prehd)\b","",title,flags=re.I)
    title = re.sub(r"\b(hindi|telugu|tamil|malayalam|english|dual|audio|dd|ddp|aac|dts|kbps|bps|movie|uncut|esub)\b","",title,flags=re.I)
    title = re.sub(r"[^a-zA-Z0-9 ]","",title)
    title = re.sub(r"\s+"," ",title).strip()

    quality="N/A"
    for q in ["2160p","1080p","720p","480p"]:
        if q in name.lower():
            quality=q
            break

    aud=[]
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada","punjabi"]:
        if a in name.lower():
            aud.append(a.capitalize())

    audio=" / ".join(sorted(set(aud))) if aud else "Unknown"

    se=""
    m=re.search(r"s(\d+)e(\d+)",name,re.I)
    if m:
        se=f"\n📺 Season {m.group(1)} Episode {m.group(2)}"

    badge="👑 Premium User\n" if premium else ""

    caption=f"""{badge}🎬 {title}

🎞 Quality : {quality}
🔊 Audio : {audio}{se}

━━━━━━━━━━━━
"""

    if CUSTOM_CAPTION:
        caption+=CUSTOM_CAPTION

    return caption

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client,message):

    user_id=message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status=await get_verify_status(user_id)
    premium=await get_premium(user_id)

    # Auto premium expire
    if premium and premium.get("expire_time"):
        if time.time()>premium["expire_time"]:
            await remove_premium(user_id)
            premium=None

    # Auto verify expire
    if verify_status['is_verified'] and verify_status.get("expire_time"):
        if time.time()>verify_status["expire_time"]:
            await update_verify_status(user_id,is_verified=False)

    # Verify token
    if message.text.startswith("/start verify_"):
        token=message.text.split("_",1)[1]
        if verify_status['verify_token']!=token:
            return await message.reply("❌ Invalid token")
        await update_verify_status(user_id,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verified successfully")

    # File fetch
    if len(message.command)>1:

        if not premium:
            if IS_VERIFY and not verify_status['is_verified']:
                return await send_verify(client,message,user_id)

        decoded=await decode(message.command[1])
        arg=decoded.split("-")

        if len(arg)==2:
            ids=[int(int(arg[1])/abs(client.db_channel.id))]
        else:
            start=int(int(arg[1])/abs(client.db_channel.id))
            end=int(int(arg[2])/abs(client.db_channel.id))
            ids=range(start,end+1)

        temp=await message.reply("📤 Fetching...")

        messages=await get_messages(client,ids)
        await temp.delete()

        sent=[]
        for msg in messages:
            caption=build_user_caption(msg,premium)

            s=await msg.copy(
                chat_id=message.chat.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                protect_content=PROTECT_CONTENT
            )
            sent.append(s)
            await asyncio.sleep(0.3)

        note=await message.reply("⚠ Auto delete in 10 minutes")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        await note.delete()
        return

    status="👑 Premium" if premium else ("✅ Verified" if verify_status['is_verified'] else "❌ Not Verified")

    await message.reply_text(
        f"Hello {message.from_user.mention}\n\nStatus: {status}",
        reply_markup=start_buttons(),
        parse_mode=ParseMode.HTML
    )

# ================= VERIFY =================

async def send_verify(client,message,user_id):
    token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
    await update_verify_status(user_id,verify_token=token,is_verified=False)

    link=await get_shortlink(
        SHORTLINK_URL,SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn=InlineKeyboardMarkup([[InlineKeyboardButton("Verify Now",url=link)]])
    await message.reply("🔐 Verification required",reply_markup=btn)

# ================= ADMIN PREMIUM =================

@Bot.on_message(filters.command("addpremium") & filters.private & filters.user(ADMINS))
async def add_premium_cmd(client,message):
    uid=int(message.command[1])
    exp=parse_time(message.command[2])
    await add_premium(uid,exp.timestamp() if exp else None)
    await message.reply("👑 Premium Activated")

@Bot.on_message(filters.command("removepremium") & filters.private & filters.user(ADMINS))
async def remove_premium_cmd(client,message):
    uid=int(message.command[1])
    await remove_premium(uid)
    await message.reply("❌ Premium Removed")

# ================= FORCE VERIFY =================

@Bot.on_message(filters.command("forceverify") & filters.private & filters.user(ADMINS))
async def force_verify(client,message):
    uid=int(message.command[1])
    exp=parse_time(message.command[2])
    await update_verify_status(uid,is_verified=True,verified_time=time.time(),expire_time=exp.timestamp() if exp else None)
    await message.reply("✅ Force verified")

@Bot.on_message(filters.command("unverify") & filters.private & filters.user(ADMINS))
async def unverify(client,message):
    uid=int(message.command[1])
    await update_verify_status(uid,is_verified=False)
    await message.reply("❌ User unverified")
