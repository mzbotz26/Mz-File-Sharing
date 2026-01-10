from pyrogram import filters
from bot import Bot
import requests
from config import TMDB_API_KEY

@Bot.on_message(filters.command("imdb"))
async def imdb_update(client, message):

    name = message.text.replace("/imdb","").strip()
    if not name:
        return await message.reply("Send movie name")

    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={name}"
    r = requests.get(url).json()

    if not r["results"]:
        return await message.reply("Not found")

    d = r["results"][0]
    await message.reply(
        f"🎬 {d['title']} ({d.get('release_date','')[:4]})\n⭐ IMDb: {d['vote_average']}/10"
    )
