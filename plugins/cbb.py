from pyrogram import __version__
from bot import Bot
from config import OWNER_ID
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ---------- START BUTTONS ----------

def start_buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ℹ️ About", callback_data="about"),
                InlineKeyboardButton("📢 Channel", url="https://t.me/ultroid_official")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ]
    )

# ---------- CALLBACK HANDLER ----------

@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "about":
        await query.message.edit_text(
            text = f"<b>○ ᴏᴡɴᴇʀ : <a href='tg://user?id={OWNER_ID}'>ᴍɪᴋᴇʏ</a>\n"
                   f"○ ᴍʏ ᴜᴘᴅᴀᴛᴇs : <a href='https://t.me/ultroid_official'>Channel</a>\n"
                   f"○ ᴍᴏᴠɪᴇs ᴜᴘᴅᴀᴛᴇs : <a href='https://t.me/MovizTube'>MovizTube</a>\n"
                   f"○ ᴏᴜʀ ᴄᴏᴍᴍᴜɴɪᴛʏ : <a href='https://t.me/ultroidofficial_chat'>Chat</a></b>",
            disable_web_page_preview = True,
            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("⚡️ Close", callback_data="close"),
                        InlineKeyboardButton("🍁 Youtube", url="https://www.youtube.com/@ultroidofficial")
                    ]
                ]
            )
        )

    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
