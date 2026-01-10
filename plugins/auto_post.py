import re, requests
from bot import Bot
from pyrogram import filters
from config import CHANNEL_ID, TMDB_API_KEY
from plugins.db import series_col

POST_CHANNEL = -1001234567890   # apna post channel id

# ---------- Helpers ----------

def clean(name):
    name = name.replace(".", " ").replace("_", " ")
    return re.sub(r"\.(mkv|mp4|avi)", "", name, flags=re.I)

def parse_series(name):
    m = re.search(r"(S\d+E\d+)", name, re.I)
    if not m:
        return None, None, None
    se = m.group(1).upper()
    title = name.split(se)[0].strip()
    season = se[:3]
    episode = se[3:]
    return title, season, episode

def tmdb_tv(title):
    url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={title}"
    r = requests.get(url, timeout=10).json()
    if r["results"]:
        d = r["results"][0]
        poster = f"https://image.tmdb.org/t/p/w500{d['poster_path']}" if d.get("poster_path") else None
        return d["id"], poster, d.get("vote_average","N/A"), d.get("first_air_date","")[:4]
    return None, None, "N/A", ""

def tmdb_episode(tv_id, season, episode):
    try:
        s = int(season[1:])
        e = int(episode[1:])
        url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{s}/episode/{e}?api_key={TMDB_API_KEY}"
        r = requests.get(url, timeout=10).json()
        return r.get("name","Episode")
    except:
        return "Episode"

def tmdb_movie(title):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    r = requests.get(url, timeout=10).json()
    if r["results"]:
        d = r["results"][0]
        poster = f"https://image.tmdb.org/t/p/w500{d['poster_path']}" if d.get("poster_path") else None
        return poster, d.get("vote_average","N/A"), d.get("release_date","")[:4]
    return None, "N/A", ""

# ---------- AUTO POST ----------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not message.document:
        return

    name = clean(message.document.file_name)

    title, season, episode = parse_series(name)

    link = f"https://t.me/{client.username}?start=file_{message.id}"

    # ---------- SERIES ----------
    if title:
        tv_id, poster, imdb, year = tmdb_tv(title)
        ep_title = tmdb_episode(tv_id, season, episode)

        line = f"🎬 {season}{episode} — {ep_title} — <a href='{link}'>Download</a>"

        data = await series_col.find_one({"title": title})

        if data:
            if line not in data["episodes"]:
                data["episodes"].append(line)
                await series_col.update_one({"title": title}, {"$set": {"episodes": data["episodes"]}})

            text = f"""📺 <b>{title} {year}</b>

⭐ IMDb: {imdb}/10

"""
            for l in data["episodes"]:
                text += l + "\n"

            text += "\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

            await client.edit_message_text(
                POST_CHANNEL,
                data["post_id"],
                text,
                parse_mode="html",
                disable_web_page_preview=True
            )

        else:
            text = f"""📺 <b>{title} {year}</b>

⭐ IMDb: {imdb}/10

{line}

Join Our Channel ♥️
👉 https://t.me/MzMoviiez
"""

            if poster:
                msg = await client.send_photo(POST_CHANNEL, poster, caption=text, parse_mode="html")
            else:
                msg = await client.send_message(POST_CHANNEL, text, parse_mode="html")

            await series_col.insert_one({
                "title": title,
                "post_id": msg.id,
                "episodes": [line]
            })

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
            await client.send_photo(POST_CHANNEL, poster, caption=caption, parse_mode="html")
        else:
            await client.send_message(POST_CHANNEL, caption, parse_mode="html")
