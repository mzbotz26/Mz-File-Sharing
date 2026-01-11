from pyrogram import filters
from bot import Bot
from config import ADMINS
from database.database import series_catalog

@Bot.on_message(filters.command("reset_catalog") & filters.private & filters.user(ADMINS))
async def reset_catalog(client, message):

    await series_catalog.delete_many({})

    await message.reply(
        "✅ <b>Catalog reset successfully!</b>\n\nAll movie & series posts are cleared.\nAuto post will start fresh now."
    )
