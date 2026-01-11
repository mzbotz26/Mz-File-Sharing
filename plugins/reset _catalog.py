# (©)Codeflix_Bots - Production Reset Catalog Plugin

from pyrogram import filters
from bot import Bot
from config import ADMINS
from database.database import series_catalog


@Bot.on_message(filters.private & filters.user(ADMINS) & filters.command("reset_catalog"), group=1)
async def reset_catalog(client, message):

    await series_catalog.delete_many({})

    await message.reply_text(
        "✅ <b>Series catalog has been reset successfully!</b>\n\n"
        "All auto-post merge data cleared.\n"
        "New movies will start fresh grouping.",
        disable_web_page_preview=True
    )
