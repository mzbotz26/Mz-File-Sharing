import time, random, string, asyncio
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, present_user


# ================= MAIN START HANDLER =================
@Bot.on_message(filters.private & filters.command("start") & subscribed)
async def start_command(client, message):

    user_id = message.from_user.id

    if not await present_user(user_id):
        await add_user(user_id)

    verify_status = await get_verify_status(user_id)

    # ===== VERIFY TOKEN =====
    if "verify_" in message.text:
        token = message.text.split("_",1)[1]

        if verify_status["verify_token"] != token:
            return await message.reply("❌ Token expired or invalid.")

        await update_verify_status(user_id, is_verified=True, verified_time=time.time())
        return await message.reply("✅ Token verified successfully! Now open your file link again.")

    # ===== FILE LINK =====
    if len(message.text.split()) > 1:

        if IS_VERIFY and not verify_status["is_verified"]:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            await update_verify_status(user_id, verify_token=token, link=message.text)

            short = await get_shortlink(
                SHORTLINK_URL,
                SHORTLINK_API,
                f"https://t.me/{client.username}?start=verify_{token}"
            )

            btn = [
                [InlineKeyboardButton("🔑 Verify Token", url=short)],
                [InlineKeyboardButton("📺 Tutorial", url=TUT_VID)]
            ]

            return await message.reply(
                "🔒 Please verify first to access this file.",
                reply_markup=InlineKeyboardMarkup(btn)
            )

        try:
            base64_string = message.text.split(" ",1)[1]
            decoded = await decode(base64_string)

            if not decoded.startswith("get-"):
                return await message.reply("❌ Invalid or expired link.")

            msg_id = int(int(decoded.split("-")[1]) / abs(client.db_channel.id))
            ids = [msg_id]

        except:
            return await message.reply("❌ Invalid or expired link.")

        wait = await message.reply("⏳ Fetching file...")

        try:
            messages = await get_messages(client, ids)
        except:
            await wait.delete()
            return await message.reply("❌ File not found!")

        await wait.delete()

        sent = []

        for msg in messages:
            try:
                s = await msg.copy(
                    chat_id=user_id,
                    caption=msg.caption.html if msg.caption else "",
                    parse_mode=ParseMode.HTML,
                    protect_content=PROTECT_CONTENT
                )
                sent.append(s)
                await asyncio.sleep(0.4)
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

    # ===== NORMAL START =====
    if IS_VERIFY and not verify_status["is_verified"]:

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(user_id, verify_token=token, link="")

        short = await get_shortlink(
            SHORTLINK_URL,
            SHORTLINK_API,
            f"https://t.me/{client.username}?start=verify_{token}"
        )

        btn = [
            [InlineKeyboardButton("🔑 Verify Token", url=short)],
            [InlineKeyboardButton("📺 Tutorial", url=TUT_VID)]
        ]

        return await message.reply(
            "🔒 Please verify to use bot.\n⏳ Valid for: "+get_exp_time(VERIFY_EXPIRE),
            reply_markup=InlineKeyboardMarkup(btn)
        )

    return await message.reply_text(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=user_id
        ),
        disable_web_page_preview=True
    )


# ================= FORCE SUB HANDLER =================
@Bot.on_message(filters.private & filters.command("start"))
async def not_joined(client, message):

    buttons = [
        [InlineKeyboardButton("Join Channel 1", url=client.invitelink)],
        [InlineKeyboardButton("Join Channel 2", url=client.invitelink2)],
        [InlineKeyboardButton("Join Channel 3", url=client.invitelink3)]
    ]

    try:
        buttons.append([InlineKeyboardButton("Now Click Here", url=f"https://t.me/{client.username}?start={message.command[1]}")])
    except:
        pass

    await message.reply(
        FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
          )
