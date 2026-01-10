import re, requests
from bot import Bot
from pyrogram import filters
from config import CHANNEL_ID, TMDB_API_KEY
from database.database import get_series, save_series, update_series_episodes

POST_CHANNEL = -1001234567890   # apna POST channel id

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def parse_series(name):
    m = re.search(r"(S\d+E\d+)", name, re.I)
    if not m:
        return None, None, None
    se = m.group(1).upper()
    title = name.split(se)[0].strip()
    return title, se[:3], se[3:]

# ---------------- TMDB ----------------

def tmdb_tv(title):
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={title}"
    r = requests.get(url, timeout=10).json()
    if r.get("results"):
        d = r["results"][0]
        return d["id"], d.get("poster_path"), d.get("vote_average"), d.get("first_air_date","")[:4]
    return None,None,"N/A",""

def tmdb_ep(tv_id, s, e):
    try:
        url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{int(s[1:])}/episode/{int(e[1:])}?api_key={TMDB_API_KEY}"
        r = requests.get(url, timeout=10).json()
        return r.get("name","Episode")
    except:
        return "Episode"

def tmdb_movie(title):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    r = requests.get(url, timeout=10).json()
    if r.get("results"):
        d = r["results"][0]
        return d.get("poster_path"), d.get("vote_average"), d.get("release_date","")[:4]
    return None,"N/A",""

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID) & filters.media)
async def auto_post(client, message):

    print("AUTO POST TRIGGERED")

    file_name = None

    if message.document:
        file_name = message.document.file_name
    elif message.video:
        file_name = message.video.file_name
    else:
        return

    if not file_name:
        return

    name = clean(file_name)
    link = f"https://t.me/{client.username}?start=file_{message.id}"

    title, season, episode = parse_series(name)

    # ---------- SERIES ----------
    if title:
        tv_id, poster, imdb, year = tmdb_tv(title)
        ep_title = tmdb_ep(tv_id, season, episode)

        line = f"🎬 {season}{episode} — {ep_title} — <a href='{link}'>Download</a>"

        data = await get_series(title)

        if data:
            eps = data["episodes"]
            if line not in eps:
                eps.append(line)
                await update_series_episodes(title, eps)

            text = f"📺 <b>{title} {year}</b>\n\n⭐ IMDb: {imdb}/10\n\n"
            for l in eps:
                text += l + "\n"
            text += "\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

            await client.edit_message_text(
                POST_CHANNEL,
                data["post_id"],
                text,
                parse_mode="html"
            )

        else:
            text = f"📺 <b>{title} {year}</b>\n\n⭐ IMDb: {imdb}/10\n\n{line}\n\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

            if poster:
                msg = await client.send_photo(
                    POST_CHANNEL,
                    f"https://image.tmdb.org/t/p/w500{poster}",
                    caption=text,
                    parse_mode="html"
                )
            else:
                msg = await client.send_message(POST_CHANNEL, text, parse_mode="html")

            await save_series(title, msg.id, [line])

    # ---------- MOVIE ----------
    else:
        movie = re.sub(r"\d{3,4}p.*","",name,flags=re.I).strip()
        poster, imdb, year = tmdb_movie(movie)

        caption = f"""🎬 {movie} {year} Hindi HDRip/WebDL

⭐ IMDb: {imdb}/10

📁 480p | x264
╰─➤ <a href="{link}">Click Here</a>

📁 720p | x264
╰─➤ <a href="{link}">Click Here</a>

📁 720p | x265
╰─➤ <a href="{link}">Click Here</a>

📁 1080p | x264
╰─➤ <a href="{link}">Click Here</a>

Join Our Channel ♥️  
👉 https://t.me/MzMoviiez
"""

        if poster:
            await client.send_photo(POST_CHANNEL, f"https://image.tmdb.org/t/p/w500{poster}", caption=caption, parse_mode="html")
        else:
            await client.send_message(POST_CHANNEL, caption, parse_mode="html")
