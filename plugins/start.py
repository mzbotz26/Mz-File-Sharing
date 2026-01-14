# © Codeflix / CodexBotz Fixed by ChatGPT

import asyncio, time, random, string
from cbb import start_buttons
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

# ================== MAIN START ==================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    # expire verify
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
                s = await msg.copy(
                    chat_id=message.chat.id,
                    caption=msg.caption.html if msg.caption else None,
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

    await message.reply_text(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=user_id
        ),
        quote=True,
        disable_web_page_preview=True
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


# ================= ADMIN =================

@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def get_users(client, message):
    users = await full_userbase()
    await message.reply(f"👥 Total Users: {len(users)}")


@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client, message):

    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast.")

    users = await full_userbase()
    total = success = fail = 0

    for uid in users:
        try:
            await message.reply_to_message.copy(uid)
            success += 1
        except UserIsBlocked:
            await del_user(uid)
            fail += 1
        except InputUserDeactivated:
            await del_user(uid)
            fail += 1
        except:
            fail += 1
        total += 1

    await message.reply(f"Broadcast Done\n\nTotal: {total}\nSuccess: {success}\nFailed: {fail}")

@Bot.on_message(filters.command("debugseries") & filters.private & filters.user(ADMINS))
async def debug_series(client, message):
    data = await get_one_series()
    await message.reply(str(data))
