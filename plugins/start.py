# © MzBotz

import asyncio, time, random, string, re
from plugins.cbb import start_buttons
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from database.database import get_one_series
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
from database.database import add_user, del_user, full_userbase, present_user

WAIT_MSG = "<b>Working...</b>"

# ================= AUTO USER CAPTION =================

def build_user_caption(msg):
    name = ""
    if msg.document:
        name = msg.document.file_name
    elif msg.video:
        name = msg.video.file_name

    title = name.rsplit(".", 1)[0]
    title = title.replace(".", " ").replace("_", " ").replace("-", " ")

    # Quality
    quality = "N/A"
    for q in ["2160p","1080p","720p","480p"]:
        if q.lower() in name.lower():
            quality = q
            break

    # Audio
    audios=[]
    for a in ["hindi","english","telugu","tamil","malayalam","marathi","kannada"]:
        if a in name.lower():
            audios.append(a.capitalize())
    audio_text = " / ".join(audios) if audios else "Unknown"

    # Season / Episode
    se_text = ""
    m = re.search(r"s(\d+)e(\d+)", name, re.I)
    if m:
        se_text = f"\n📺 Season {int(m.group(1))} Episode {int(m.group(2))}"

    caption = f"""🎬 {title}

🎞 Quality : {quality}
🔊 Audio : {audio_text}{se_text}

━━━━━━━━━━━━
"""

    if CUSTOM_CAPTION:
        caption += CUSTOM_CAPTION

    return caption

# ================== MAIN START ==================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await update_verify_status(user_id, is_verified=False)

    # ================= VERIFY TOKEN =================

    if message.text.startswith("/start verify_"):
        token = message.text.split("_",1)[1]

        if verify_status['verify_token'] != token:
            return await message.reply("❌ Invalid or expired token. Use /start again.")

        await update_verify_status(user_id, is_verified=True, verified_time=time.time())
        return await message.reply("✅ Token verified successfully. Now click your file link again.")

    # ================= FILE FETCH =================

    if len(message.command) > 1:

        if IS_VERIFY and not verify_status['is_verified']:
            return await send_verify(client, message, user_id)

        base64_string = message.command[1]

        try:
            decoded = await decode(base64_string)
            arg = decoded.split("-")
        except:
            return await message.reply("❌ Invalid or expired link.")

        if len(arg) == 2:
            ids = [int(int(arg[1]) / abs(client.db_channel.id))]
        elif len(arg) == 3:
            start = int(int(arg[1]) / abs(client.db_channel.id))
            end = int(int(arg[2]) / abs(client.db_channel.id))
            ids = range(start, end+1)
        else:
            return await message.reply("❌ Invalid or expired link.")

        temp = await message.reply("📤 Fetching your file...")

        try:
            messages = await get_messages(client, ids)
        except:
            return await temp.edit("❌ File not found.")

        await temp.delete()

        sent = []

        for msg in messages:
            try:
                caption = build_user_caption(msg)

                s = await msg.copy(
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

        note = await message.reply("⚠ Files will auto delete after 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try:
                await m.delete()
            except:
                pass
        try:
            await note.delete()
        except:
            pass

        return

    # ================= NORMAL START =================

    status_text = "✅ Verified" if verify_status['is_verified'] else "❌ Not Verified"
    expire_text = "∞" if verify_status['is_verified'] else get_exp_time(VERIFY_EXPIRE)

    text = f"""ʜᴇʟʟᴏ {message.from_user.mention}

ɪ ᴀᴍ ᴍᴜʟᴛɪ ғɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ , ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ɪɴ sᴘᴇᴄɪғɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ɪᴛ ғʀᴏᴍ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ » @visionloverz

━━━━━━━━━━━━━━
🔐 Verification : {status_text}
⏳ Expiry : {expire_text}
━━━━━━━━━━━━━━
"""

    if START_PIC:
        await client.send_photo(
            chat_id=message.chat.id,
            photo=START_PIC,
            caption=text,
            reply_markup=start_buttons(),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.reply_text(
            text,
            reply_markup=start_buttons(),
            disable_web_page_preview=True,
            quote=True
        )

# ================= FORCE SUB HANDLER =================

@Bot.on_message(filters.command("start") & filters.private)
async def not_joined(client, message):

    buttons = [
        [
            InlineKeyboardButton("Join Channel 1", url=client.invitelink),
            InlineKeyboardButton("Join Channel 2", url=client.invitelink2),
        ],
        [
            InlineKeyboardButton("Join Channel 3", url=client.invitelink3)
        ]
    ]

    try:
        buttons.append(
            [InlineKeyboardButton("Now Click Here", url=f"https://t.me/{client.username}?start={message.command[1]}")]
        )
    except:
        pass

    await message.reply_text(
        FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True
    )

# ================= VERIFY FUNCTION =================

async def send_verify(client, message, user_id):

    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    await update_verify_status(user_id, verify_token=token, is_verified=False)

    link = await get_shortlink(
        SHORTLINK_URL,
        SHORTLINK_API,
        f"https://t.me/{client.username}?start=verify_{token}"
    )

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("Verify Now", url=link)],
        [InlineKeyboardButton("How To Use", url=TUT_VID)]
    ])

    await message.reply(
        f"🔐 Verification Required\n\nToken valid for: {get_exp_time(VERIFY_EXPIRE)}",
        reply_markup=btn,
        quote=True
    )
