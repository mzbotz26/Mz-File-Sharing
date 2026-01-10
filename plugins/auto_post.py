import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def parse_series(name):
    m = re.search(r"S(\d+)E(\d+)", name, re.I)
    if not m:
        return None,None,None
    return m.group(1), m.group(2), name.split(m.group(0))[0].strip()

def tmdb_tv(title):
    r = requests.get(f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={title}").json()
    if r["results"]:
        d=r["results"][0]
        return d["id"],d.get("poster_path"),d.get("vote_average"),d.get("first_air_date","")[:4]
    return None,None,"N/A",""

def tmdb_ep(tv,s,e):
    r=requests.get(f"https://api.themoviedb.org/3/tv/{tv}/season/{s}/episode/{e}?api_key={TMDB_API_KEY}").json()
    return r.get("name","Episode")

def tmdb_movie(title):
    r=requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}").json()
    if r["results"]:
        d=r["results"][0]
        return d.get("poster_path"),d.get("vote_average"),d.get("release_date","")[:4]
    return None,"N/A",""

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not message.document:
        return

    name = clean(message.document.file_name)

    code = await encode(f"get-{client.db_channel.id}-{message.id}")
    link = f"https://t.me/{client.username}?start={code}"

    season,episode,title = parse_series(name)

    # ===== SERIES =====
    if season:
        tv,poster,imdb,year = tmdb_tv(title)
        ep_title = tmdb_ep(tv,season,episode)
        line=f"📺 S{season}E{episode} — {ep_title} — <a href='{link}'>Download</a>"

        data=await get_series(title)

        if data:
            eps=data["episodes"]
            if line not in eps:
                eps.append(line)
                await update_series_episodes(title,eps)

            txt=f"<b>{title} {year}</b>\n⭐ IMDb: {imdb}/10\n\n"
            for x in eps: txt+=x+"\n"
            txt+="\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

            await client.edit_message_text(POST_CHANNEL,data["post_id"],txt,parse_mode=ParseMode.HTML)

        else:
            txt=f"<b>{title} {year}</b>\n⭐ IMDb: {imdb}/10\n\n{line}\n\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

            if poster:
                m=await client.send_photo(POST_CHANNEL,f"https://image.tmdb.org/t/p/w500{poster}",caption=txt,parse_mode=ParseMode.HTML)
            else:
                m=await client.send_message(POST_CHANNEL,txt,parse_mode=ParseMode.HTML)

            await save_series(title,m.id,[line])

    # ===== MOVIE =====
    else:
        movie=re.sub(r"\(.*?\)|\d{3,4}p.*","",name,flags=re.I).strip()
        poster,imdb,year=tmdb_movie(movie)

        txt=f"""🎬 {movie} ({year}) Hindi HDRip/WebDL

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
            await client.send_photo(POST_CHANNEL,f"https://image.tmdb.org/t/p/w500{poster}",caption=txt,parse_mode=ParseMode.HTML)
        else:
            await client.send_message(POST_CHANNEL,txt,parse_mode=ParseMode.HTML)
