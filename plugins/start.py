import time, random, string, asyncio
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait

from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, full_userbase, present_user

# ================= START =================

@Bot.on_message(filters.command("start") & filters.private & subscribed)
async def start_command(client, message):

    uid = message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    verify = await get_verify_status(uid)

    if "verify_" in message.text:
        token = message.text.split("_",1)[1]
        if verify["verify_token"] != token:
            return await message.reply("❌ Token expired or invalid.")
        await update_verify_status(uid,is_verified=True,verified_time=time.time())
        return await message.reply("✅ Verified successfully. Open link again.")

    if len(message.text.split())>1:

        if IS_VERIFY and not verify["is_verified"]:
            token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
            await update_verify_status(uid,verify_token=token)
            short = await get_shortlink(SHORTLINK_URL,SHORTLINK_API,f"https://t.me/{client.username}?start=verify_{token}")

            return await message.reply("🔒 Verify first to access file.",reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Verify",url=short)],
                [InlineKeyboardButton("📺 Tutorial",url=TUT_VID)]
            ]))

        try:
            code=message.text.split()[1]
            decoded=await decode(code)
            msg_id=int(int(decoded.split("-")[1])/abs(client.db_channel.id))
            ids=[msg_id]
        except:
            return await message.reply("❌ Invalid or expired link.")

        wait=await message.reply("⏳ Fetching file...")
        msgs=await get_messages(client,ids)
        await wait.delete()

        sent=[]
        for m in msgs:
            try:
                s=await m.copy(uid,parse_mode=ParseMode.HTML,protect_content=PROTECT_CONTENT)
                sent.append(s)
            except FloodWait as e:
                await asyncio.sleep(e.x)

        warn=await message.reply("⚠ Files will auto delete in 10 minutes.")
        await asyncio.sleep(600)
        for m in sent:
            try: await m.delete()
            except: pass
        await warn.delete()
        return

    if IS_VERIFY and not verify["is_verified"]:
        token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
        await update_verify_status(uid,verify_token=token)
        short=await get_shortlink(SHORTLINK_URL,SHORTLINK_API,f"https://t.me/{client.username}?start=verify_{token}")
        return await message.reply("🔒 Verify token first.",reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 Verify",url=short)],
            [InlineKeyboardButton("📺 Tutorial",url=TUT_VID)]
        ]))

    await message.reply(START_MSG.format(first=message.from_user.first_name))

# ================= FORCE SUB FALLBACK =================

@Bot.on_message(filters.command("start") & filters.private)
async def force_sub_handler(client,message):
    buttons=[
        [InlineKeyboardButton("Join Channel 1",url=client.invitelink)],
        [InlineKeyboardButton("Join Channel 2",url=client.invitelink2)],
        [InlineKeyboardButton("Join Channel 3",url=client.invitelink3)],
        [InlineKeyboardButton("Try Again",url=f"https://t.me/{client.username}?start")]
    ]
    await message.reply(FORCE_MSG.format(first=message.from_user.first_name),
        reply_markup=InlineKeyboardMarkup(buttons))

# ================= USERS =================

@Bot.on_message(filters.command("users") & filters.private & filters.user(ADMINS))
async def users(client,message):
    users=await full_userbase()
    await message.reply(f"👥 Total Users: {len(users)}")

# ================= BROADCAST =================

@Bot.on_message(filters.command("broadcast") & filters.private & filters.user(ADMINS))
async def broadcast(client,message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message.")

    users=await full_userbase()
    sent=0
    for u in users:
        try:
            await message.reply_to_message.copy(u)
            sent+=1
        except:
            pass
    await message.reply(f"✅ Broadcast sent to {sent} users.")
