from bot import Bot
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent
from database.database import requests_col

@Bot.on_inline_query()
async def inline_req(client, query):

    q = query.query.lower().strip()
    if not q:
        return await query.answer([], cache_time=1)

    cursor = requests_col.find({"request":{"$regex":q,"$options":"i"}}).limit(20)

    results = []
    async for r in cursor:
        results.append(
            InlineQueryResultArticle(
                title=r["request"],
                description=f"Status: {r['status']}",
                input_message_content=InputTextMessageContent(
                    f"📥 <b>{r['request']}</b>\nStatus: {r['status']}",
                    parse_mode="html"
                )
            )
        )

    await query.answer(results, cache_time=5)
