from pyrogram import filters
from bot import Bot
from helper_func import decode,get_messages,subscribed
from pyrogram.enums import ParseMode
import asyncio

@Bot.on_message(filters.private & filters.command("start") & subscribed)
async def start(client,message):

    if len(message.command) < 2:
        return await message.reply("Send a file link from channel.")

    payload = message.command[1]

    try:
        decoded = await decode(payload)
        if not decoded.startswith("get-"):
            return await message.reply("❌ Invalid or expired link.")

        msg_id = int(decoded.replace("get-",""))
    except:
        return await message.reply("❌ Invalid or expired link.")

    temp=await message.reply("⏳ Fetching file...")

    try:
        msgs=await get_messages(client,[msg_id])
    except:
        await temp.delete()
        return await message.reply("❌ File not found.")

    await temp.delete()

    for m in msgs:
        try:
            await m.copy(message.from_user.id,
                         caption=m.caption.html if m.caption else "",
                         parse_mode=ParseMode.HTML)
            await asyncio.sleep(0.4)
        except:
            pass
