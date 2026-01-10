from bot import Bot
from pyrogram import filters
from database.database import approve_request
from config import ADMINS

@Bot.on_message(filters.private & filters.command("approve") & filters.user(ADMINS))
async def approve(client, message):

    if len(message.command) < 2:
        return await message.reply("Use:\n/approve Request Name")

    q = message.text.split(" ",1)[1]

    data = await approve_request(q)
    if not data:
        return await message.reply("❌ Request not found")

    try:
        await client.send_message(data["user_id"], f"🎉 Your request approved:\n\n<b>{q}</b>", parse_mode="html")
    except:
        pass

    await message.reply("✅ Request approved & user notified.")
