import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"x264|x265|hevc|webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def tmdb_fetch(title):
    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]
    return (
        d.get("poster_path"),
        round(d.get("vote_average",0),1),
        d.get("release_date","")[:4],
        d.get("overview","N/A"),
        " / ".join([str(x) for x in d.get("genre_ids",[])]),
        d.get("original_language","N/A").upper()
    )

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    fname = message.document.file_name if message.document else message.video.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    db_title = title.lower()

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title)

    line = f"📁 File\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(db_title)

    caption = f"""🎬 {title} ({year})

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang}

📖 Story:
{story}

"""

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        for e in eps:
            caption += e + "\n\n"

        caption += "Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        # 🔥 THIS IS THE REAL FIX
        await client.edit_message_caption(
            POST_CHANNEL,
            old["post_id"],
            caption,
            parse_mode=ParseMode.HTML
        )
        return

    caption += line + "\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL, caption, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, [line])
