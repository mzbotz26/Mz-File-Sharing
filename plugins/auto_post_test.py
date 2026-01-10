from bot import Bot
from pyrogram import filters
from config import CHANNEL_ID, POST_CHANNEL

@Bot.on_message(filters.chat(CHANNEL_ID))
async def test_auto_post(client, message):
    print("AUTO POST TRIGGERED FROM:", message.chat.id)
    await client.send_message(POST_CHANNEL, "✅ Auto post system working")
