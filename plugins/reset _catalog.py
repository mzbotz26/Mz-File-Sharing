from pyrogram import filters
from bot import Bot
from config import ADMINS
from database.database import series_catalog

@Bot.on_message(filters.command("reset_catalog") & filters.private & filters.user(ADMINS))
async def reset_catalog(client, message):
    try:
        result = await series_catalog.delete_many({})
        await message.reply(
            f"✅ Catalog Reset Successful!\n\nDeleted Records: {result.deleted_count}"
        )
    except Exception as e:
        await message.reply(f"❌ Error while resetting catalog:\n{e}")
