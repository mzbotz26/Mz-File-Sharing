# (©)Codeflix_Bots - Fixed Production

import logging, random, string, time, asyncio

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, del_user, full_userbase, present_user


# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client: Client, message: Message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    # -------- VERIFY EXPIRE CHECK --------
    if verify_status["is_verified"] and VERIFY_EXPIRE < (time.time() - verify_status["verified_time"]):
        await update_verify_status(user_id, is_verified=False)

    # -------- VERIFY TOKEN --------
    if "verify_" in message.text:
        token = message.text.split("_", 1)[1]

        if verify_status["verify_token"] != token:
            return await message.reply("❌ Token expired or invalid.")

        await update_verify_status(user_id, is_verified=True, verified_time=time.time())

        if verify_status["link"]:
            return await client.send_message(user_id, verify_status["link"])

        return await message.reply("✅ Token verified successfully! Now open your file link again.")

    # -------- FILE LINK --------
    if len(message.text.split()) > 1:

        if IS_VERIFY and not verify_status["is_verified"]:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await update_verify_status(user_id, verify_token=token, link=message.text)

            short = await get_shortlink(
                SHORTLINK_URL,
                SHORTLINK_API,
                f"https://t.me/{client.username}?start=verify_{token}"
            )

            return await message.reply(
                "🔒 Please verify first to access this file.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 Verify Token", url=short)],
                    [InlineKeyboardButton("📺 Tutorial", url=TUT_VID)]
                ])
            )

        try:
            base64_string = message.text.split(" ", 1)[1]
            decoded = await decode(base64_string)

            if not decoded.startswith("get-"):
                return await message.reply("❌ Invalid or expired link.")

            parts = decoded.split("-")

            if len(parts) == 3:
                start = int(int(parts[1]) / abs(client.db_channel.id))
                end = int(int(parts[2]) / abs(client.db_channel.id))
                ids = range(start, end+1)
            else:
                ids = [int(int(parts[1]) / abs(client.db_channel.id))]

        except:
            return await message.reply("❌ Invalid or expired link.")

        temp = await message.reply("⏳ Please wait...")

        try:
            messages = await get_messages(client, ids)
        except:
            await temp.delete()
            return await message.reply("❌ Something went wrong!")

        await temp.delete()

        sent = []

        for msg in messages:
            try:
                caption = msg.caption.html if msg.caption else ""
                s = await msg.copy(user_id, caption=caption, parse_mode=ParseMode.HTML, protect_content=PROTECT_CONTENT)
                sent.append(s)
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except:
                pass

        warn = await message.reply("⚠ Files will auto delete in 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass

        try: await warn.delete()
        except: pass

        return

    # -------- NORMAL START --------
    if verify_status["is_verified"]:
        return await message.reply_text(
            START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=user_id
            ),
            disable_web_page_preview=True
        )

    # -------- VERIFY REQUIRED --------
    if IS_VERIFY and not verify_status["is_verified"]:

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, link="")

        short = await get_shortlink(
            SHORTLINK_URL,
            SHORTLINK_API,
            f"https://t.me/{client.username}?start=verify_{token}"
        )

        return await message.reply(
            f"🔒 Token expired.\n\n⏳ Valid for: {get_exp_time(VERIFY_EXPIRE)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Verify Token", url=short)],
                [InlineKeyboardButton("📺 Tutorial", url=TUT_VID)]
            ])
        )


# ================= FORCE SUB =================

@Bot.on_message(filters.command("start") & filters.private)
async def not_joined(client: Client, message: Message):

    buttons = [
        [InlineKeyboardButton("Join Channel 1", url=client.invitelink)],
        [InlineKeyboardButton("Join Channel 2", url=client.invitelink2)],
        [InlineKeyboardButton("Join Channel 3", url=client.invitelink3)]
    ]

    try:
        buttons.append([
            InlineKeyboardButton("Try Again", url=f"https://t.me/{client.username}?start={message.command[1]}")
        ])
    except:
        pass

    await message.reply(
        FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )
