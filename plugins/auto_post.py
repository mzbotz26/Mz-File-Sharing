from bot import Bot
from pyrogram import filters
from config import CHANNEL_ID

POST_CHANNEL = -1001678291887   # <-- apna post channel id daalo

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video or message.audio):
        return

    try:
        await message.copy(POST_CHANNEL)
    except Exception as e:
        print("AUTO POST ERROR:", e)
