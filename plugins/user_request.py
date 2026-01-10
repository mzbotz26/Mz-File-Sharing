from bot import Bot
from pyrogram import filters
from database.database import add_request

@Bot.on_message(filters.private & filters.command("request"))
async def user_request(client, message):
    if len(message.command) < 2:
        return await message.reply("Use:\n/request Movie or Series Name")

    q = message.text.split(" ",1)[1]
    await add_request(message.from_user.id, message.from_user.first_name, q)

    await message.reply(f"✅ Request submitted:\n\n<b>{q}</b>", parse_mode="html")
