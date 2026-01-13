import re, requests, asyncio
import PTN
from thefuzz import fuzz
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- SORT ----------------

def natural_sort_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s or "")]

# ---------------- DETECT ----------------

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdtc","prehd"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def detect_audio(name):
    name=name.lower()
    if "multi" in name: return "Multi Audio"
    if "dual" in name: return "Dual Audio"
    return "Single Audio"

def detect_languages(name):
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi","korean","japanese"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " + ".join(langs) if langs else "Unknown"

# ---------------- PARSER ----------------

async def clean_and_parse_filename(name):

    parsed = PTN.parse(name.replace("_"," ").replace("."," "))

    raw_title = parsed.get("title","").strip()
    title = raw_title.title()

    year = parsed.get("year")

    season = parsed.get("season")
    episode = parsed.get("episode")

    season_str = f"S{int(season):02d}" if season else ""
    episode_str = f"E{int(episode):02d}" if episode else ""

    is_series = bool(season or episode)

    display_title = title
    if season_str:
        display_title += f" {season_str}"
    if year:
        display_title += f" ({year})"

    batch_title = f"{title} {season_str}".strip().lower()

    return {
        "title": display_title,
        "batch_title": batch_title,
        "year": year,
        "season": season_str,
        "episode": episode_str,
        "is_series": is_series
    }

# ---------------- TMDB ----------------

def tmdb_fetch(title,is_series=False):
    url="tv" if is_series else "movie"
    try:
        r=requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d=r["results"][0]
    poster=d.get("poster_path")
    rating=str(d.get("vote_average","N/A"))
    year=(d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story=d.get("overview","N/A")
    genres=" / ".join([str(x) for x in d.get("genre_ids",[])]) or "N/A"

    return poster,rating,year,story,genres

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name

    info = await clean_and_parse_filename(fname)

    title = info["title"]
    merge_key = info["batch_title"]
    season = info["season"]
    episode = info["episode"]
    is_series = info["is_series"]

    source = detect_source(fname)
    audio = detect_audio(fname)
    languages = detect_languages(fname)

    poster,rating,tmdb_year,story,genres = tmdb_fetch(title,is_series)

    year = info["year"] or tmdb_year or "N/A"

    size = media.file_size
    size_mb=round(size/1024/1024,2)
    size_text=f"{size_mb} MB" if size_mb<1024 else f"{round(size_mb/1024,2)} GB"

    code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    ep_tag=f"{season}{episode}" if season or episode else ""

    line=f"📂 ➤ {ep_tag} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    head=f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {year}
<b>📕 Story:</b> {story}

"""

    footer=f"""

<b>🔊 Audio :</b> {audio} ({languages})

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old=await get_series(merge_key)

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)

        eps.sort(key=natural_sort_key)
        await update_series_episodes(merge_key,eps)

        body="\n".join(eps)
        text=head+body+footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text=head+line+footer

    if poster:
        msg=await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(merge_key,msg.id,[line])
