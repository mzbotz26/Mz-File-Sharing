import time, random, string, asyncio
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, present_user, full_userbase

@Bot.on_message(filters.private & filters.command("start") & subscribed)
async def start_command(client, message):

    uid=message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    verify=await get_verify_status(uid)

    if "verify_" in message.text:
        token=message.text.split("_",1)[1]
        if verify["verify_token"]!=token:
            return await message.reply("❌ Token expired or invalid.")
        await update_verify_status(uid,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Token verified successfully! Now open your link again.")

    if len(message.text.split())>1:

        if IS_VERIFY and not verify["is_verified"]:
            token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
            await update_verify_status(uid,verify_token=token,link=message.text)

            short=await get_shortlink(SHORTLINK_URL,SHORTLINK_API,f"https://t.me/{client.username}?start=verify_{token}")

            return await message.reply("🔒 Please verify first.",reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Verify Token",url=short)],
                [InlineKeyboardButton("📺 Tutorial",url=TUT_VID)]
            ]))

        try:
            b64=message.text.split(" ",1)[1]
            decoded=await decode(b64)
            msg_id=int(int(decoded.split("-")[1])/abs(client.db_channel.id))
        except:
            return await message.reply("❌ Invalid or expired link.")

        temp=await message.reply("⏳ Fetching file...")

        try:
            msgs=await get_messages(client,[msg_id])
        except:
            await temp.delete()
            return await message.reply("❌ File not found.")

        await temp.delete()

        sent=[]
        for m in msgs:
            try:
                s=await m.copy(uid,caption=m.caption.html if m.caption else "",parse_mode=ParseMode.HTML,protect_content=PROTECT_CONTENT)
                sent.append(s)
                await asyncio.sleep(0.4)
            except FloodWait as e:
                await asyncio.sleep(e.x)

        warn=await message.reply("⚠ Auto delete in 10 minutes.")
        await asyncio.sleep(600)

        for m in sent:
            try: await m.delete()
            except: pass
        try: await warn.delete()
        except: pass
        return

    if IS_VERIFY and not verify["is_verified"]:
        token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
        await update_verify_status(uid,verify_token=token,link="")
        short=await get_shortlink(SHORTLINK_URL,SHORTLINK_API,f"https://t.me/{client.username}?start=verify_{token}")
        return await message.reply("🔒 Verify to continue.",reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Verify Token",url=short)],
            [InlineKeyboardButton("📺 Tutorial",url=TUT_VID)]
        ]))

    return await message.reply_text(START_MSG.format(
        first=message.from_user.first_name,
        last=message.from_user.last_name,
        username=message.from_user.username,
        mention=message.from_user.mention,
        id=uid
    ),disable_web_page_preview=True)

@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def users(client,message):
    u=await full_userbase()
    await message.reply(f"Total Users: {len(u)}")
