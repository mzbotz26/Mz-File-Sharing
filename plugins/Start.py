# © MzBotz

import asyncio, time, random, string, re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from plugins.cbb import start_buttons
from bot import Bot
from config import *
from helper_func import (
    subscribed, encode, decode, get_messages,
    get_shortlink, get_verify_status, update_verify_status, get_exp_time
)
from database.database import (
    add_user, del_user, full_userbase, present_user
)

BOT_START_TIME = time.time()

WAIT_MSG = "<b>Working...</b>"

# ================= CLEAN USER CAPTION =================

def build_user_caption(msg):
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

    caption=f"""🎬 {title}

🎞 Quality : {quality}
🔊 Audio : {audio}

━━━━━━━━━━━━
"""

    if CUSTOM_CAPTION:
        caption+=CUSTOM_CAPTION

    return caption

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client,message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    # Verify token
    if message.text.startswith("/start verify_"):
        token = message.text.split("_",1)[1]
        if verify_status['verify_token'] != token:
            return await message.reply("❌ Invalid or expired token.")
        await update_verify_status(user_id,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verified successfully. Click file link again.")

    # File fetch
    if len(message.command) > 1:

        if IS_VERIFY and not verify_status['is_verified']:
            return await send_verify(client,message,user_id)

        decoded = await decode(message.command[1])
        arg = decoded.split("-")

        if len(arg)==2:
            ids=[int(int(arg[1])/abs(client.db_channel.id))]
        else:
            start=int(int(arg[1])/abs(client.db_channel.id))
            end=int(int(arg[2])/abs(client.db_channel.id))
            ids=range(start,end+1)

        temp = await message.reply("📤 Fetching your file...")

        messages = await get_messages(client,ids)
        await temp.delete()

        sent=[]
        for msg in messages:
            caption = build_user_caption(msg)

            s = await msg.copy(
                chat_id=message.chat.id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                protect_content=PROTECT_CONTENT
            )
            sent.append(s)
            await asyncio.sleep(0.4)

        note = await message.reply("⚠ Files will auto delete after 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        await note.delete()
        return

    await message.reply_text(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=user_id
        ),
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

# ================= USERS =================

@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client,message):
    users=await full_userbase()
    await message.reply(f"👥 Total Users: {len(users)}")

# ================= BROADCAST =================

@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client,message):

    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast.")

    users=await full_userbase()
    total=success=fail=0

    for uid in users:
        try:
            await message.reply_to_message.copy(uid)
            success+=1
        except:
            fail+=1
        total+=1

    await message.reply(f"Broadcast Done\n\nTotal: {total}\nSuccess: {success}\nFailed: {fail}")

# ================= STATS =================

@Bot.on_message(filters.command("stats") & filters.private & filters.user(ADMINS))
async def stats(client,message):
    uptime=int(time.time()-BOT_START_TIME)
    h=uptime//3600
    m=(uptime%3600)//60
    s=uptime%60
    await message.reply(f"🤖 Bot Uptime:\n{h}h {m}m {s}s")

# ================= GENLINK =================

@Bot.on_message(filters.command("genlink") & filters.private & filters.user(ADMINS))
async def genlink(client,message):
    if not message.reply_to_message:
        return await message.reply("Reply to a post.")

    msg=message.reply_to_message
    code=await encode(f"get-{msg.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"
    await message.reply(f"🔗 Link:\n{link}")

# ================= BATCH =================

@Bot.on_message(filters.command("batch") & filters.private & filters.user(ADMINS))
async def batch(client,message):
    if len(message.command)!=3:
        return await message.reply("Use: /batch start_id end_id")

    s=int(message.command[1])
    e=int(message.command[2])

    code=await encode(f"get-{s*abs(client.db_channel.id)}-{e*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    await message.reply(f"📦 Batch Link:\n{link}")
