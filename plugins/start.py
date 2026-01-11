import time, random, string, asyncio
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from bot import Bot
from config import *
from helper_func import *
from database.database import add_user, full_userbase, present_user

# ---------------- START (SUBSCRIBED) ----------------

@Bot.on_message(filters.private & filters.command("start") & subscribed)
async def start(client,message):

    uid=message.from_user.id

    if not await present_user(uid):
        await add_user(uid)

    verify=await get_verify_status(uid)

    if verify["is_verified"] and VERIFY_EXPIRE < (time.time()-verify["verified_time"]):
        await update_verify_status(uid,is_verified=False)

    # ---------- VERIFY CALLBACK ----------
    if "verify_" in message.text:
        token=message.text.split("_",1)[1]
        if verify["verify_token"]!=token:
            return await message.reply("❌ Token expired or invalid.")

        await update_verify_status(uid,is_verified=True,verified_time=time.time())
        if verify["link"]:
            return await client.send_message(uid,verify["link"])
        return await message.reply("✅ Token verified. Open file link again.")

    # ---------- FILE LINK ----------
    if len(message.command)>1:

        if IS_VERIFY and not verify["is_verified"]:
            token=''.join(random.choices(string.ascii_letters+string.digits,k=10))
            await update_verify_status(uid,verify_token=token,link=message.text)

            short=await get_shortlink(SHORTLINK_URL,SHORTLINK_API,f"https://t.me/{client.username}?start=verify_{token}")

            btn=[[InlineKeyboardButton("🔑 Verify Token",url=short)],
                 [InlineKeyboardButton("📺 Tutorial",url=TUT_VID)]]

            return await message.reply("🔒 Please verify first to access file.",reply_markup=InlineKeyboardMarkup(btn))

        try:
            code=message.text.split(" ",1)[1]
            dec=await decode(code)
            msg_id=int(int(dec.split("-")[1])/abs(client.db_channel.id))
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
            except: pass

        warn=await message.reply("⚠ Files auto delete in 10 minutes.")
        await asyncio.sleep(600)

        for x in sent:
            try: await x.delete()
            except: pass
        try: await warn.delete()
        except: pass
        return

    # ---------- NORMAL START ----------
    return await message.reply_text(
        START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=message.from_user.username,
            mention=message.from_user.mention,
            id=uid
        ),
        disable_web_page_preview=True
    )

# ---------------- FORCE SUB ----------------

@Bot.on_message(filters.private & filters.command("start"))
async def force_sub(client,message):

    btn=[
        [InlineKeyboardButton("Join Channel 1",url=client.invitelink)],
        [InlineKeyboardButton("Join Channel 2",url=client.invitelink2)],
        [InlineKeyboardButton("Join Channel 3",url=client.invitelink3)],
    ]

    if len(message.command)>1:
        btn.append([InlineKeyboardButton("Try Again",url=f"https://t.me/{client.username}?start={message.command[1]}")])

    await message.reply(
        FORCE_MSG.format(first=message.from_user.first_name),
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ---------------- USERS ----------------

@Bot.on_message(filters.private & filters.command("users") & filters.user(ADMINS))
async def users(client,message):
    u=await full_userbase()
    await message.reply(f"👥 Total Users: {len(u)}")

# ---------------- BROADCAST ----------------

@Bot.on_message(filters.private & filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client,message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message.")
    users=await full_userbase()
    sent=0
    for u in users:
        try:
            await message.reply_to_message.copy(u)
            sent+=1
        except: pass
    await message.reply(f"✅ Broadcast sent to {sent} users.")
