import time, random, string, asyncio
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, full_userbase, present_user


@Bot.on_message(filters.private & filters.command("start"))
async def start_command(client: Bot, message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    # ================= VERIFY CALLBACK =================

    if "verify_" in message.text:
        _, token = message.text.split("_", 1)

        if verify_status["verify_token"] != token:
            return await message.reply("❌ Token expired or invalid.")

        await update_verify_status(user_id, is_verified=True, verified_time=time.time())

        if verify_status.get("link"):
            return await client.send_message(user_id, verify_status["link"])

        return await message.reply("✅ Verification successful!")

    # ================= FILE LINK =================

    if len(message.text.split()) > 1:

        if IS_VERIFY and not verify_status["is_verified"]:

            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await update_verify_status(user_id, verify_token=token, link=message.text)

            short = await get_shortlink(
                SHORTLINK_URL,
                SHORTLINK_API,
                f"https://t.me/{client.username}?start=verify_{token}"
            )

            buttons = [
                [InlineKeyboardButton("🔐 Verify Access", url=short)],
                [InlineKeyboardButton("📺 How to Verify", url=TUT_VID)]
            ]

            return await message.reply(
                "🔒 Please verify to access this file.",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        try:
            base64_string = message.text.split(" ", 1)[1]
            decoded = await decode(base64_string)

            if not decoded.startswith("get-"):
                return await message.reply("❌ Invalid or expired link.")

            msg_id = int(int(decoded.split("-")[1]) / abs(client.db_channel.id))

        except:
            return await message.reply("❌ Invalid or expired link.")

        temp = await message.reply("⏳ Fetching your file...")

        try:
            messages = await get_messages(client, [msg_id])
        except:
            await temp.delete()
            return await message.reply("❌ File not found!")

        await temp.delete()

        for msg in messages:
            try:
                await msg.copy(
                    chat_id=user_id,
                    caption=msg.caption.html if msg.caption else "",
                    parse_mode=ParseMode.HTML,
                    protect_content=PROTECT_CONTENT
                )
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except:
                pass

        return await message.reply("✅ File delivered successfully!")

    # ================= NORMAL START =================

    if IS_VERIFY and not verify_status["is_verified"]:

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, link="")

        short = await get_shortlink(
            SHORTLINK_URL,
            SHORTLINK_API,
            f"https://t.me/{client.username}?start=verify_{token}"
        )

        buttons = [
            [InlineKeyboardButton("🔐 Verify Access", url=short)],
            [InlineKeyboardButton("📺 How to Verify", url=TUT_VID)]
        ]

        return await message.reply(
            "🔒 Verification required to use this bot.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    return await message.reply_text(START_MSG)
