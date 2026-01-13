import re, requests
import PTN
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN TITLE ----------------

def normalize_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\s+"," ",name)
    return name.strip()

# ---------------- DETECT META ----------------

def detect_source(n):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdtc","prehd"]:
        if s in n: return s.upper()
    return "WEB-DL"

def detect_resolution(n):
    if "2160" in n: return "2160p"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def detect_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def detect_audio(n):
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi","korean","japanese","french","spanish"]:
        if l in n:
            langs.append(l.capitalize())
    return " ".join(sorted(set(langs))) if langs else "Unknown"

def detect_audio_type(n):
    if "multi" in n: return "Multi Audio"
    if "dual" in n: return "Dual Audio"
    return "Single Audio"

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
    rating=str(round(d.get("vote_average",0),1))
    year=(d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story=d.get("overview","N/A")

    genres=[]
    for g in d.get("genre_ids",[]):
        genres.append(str(g))

    return poster,rating,year,story," / ".join(genres) if genres else "N/A"

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name.lower()
    size = media.file_size

    parsed = PTN.parse(fname)

    title = parsed.get("title","")
    year = parsed.get("year")
    season = parsed.get("season")
    episode = parsed.get("episode")

    title = normalize_title(title)

    is_series = True if season or episode else False

    res = detect_resolution(fname)
    codec = detect_codec(fname)
    source = detect_source(fname)
    audio_type = detect_audio_type(fname)
    languages = detect_audio(fname)

    poster,rating,tmdb_year,story,genres = tmdb_fetch(title,is_series)

    show_year = year or tmdb_year or "N/A"

    # ---------- MERGE KEY ----------
    merge_key = f"{title.lower()}_{show_year}"
    if is_series and season:
        merge_key += f"_s{season}"

    # ---------- LINK ----------
    code = await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb=round(size/1024/1024,2)
    size_text=f"{size_mb} MB" if size_mb<1024 else f"{round(size_mb/1024,2)} GB"

    ep_tag=""
    if season and episode:
        ep_tag=f"S{int(season):02d}E{int(episode):02d}"

    line = f"📂 ➤ {ep_tag} {res} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    head=f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer=f"""

<b>🔊 Audio :-</b> {audio_type} ({languages})

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old = await get_series(merge_key)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(merge_key, eps)

        eps_sorted = sorted(eps)
        text = head + "\n".join(eps_sorted) + footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text = head + line + footer

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(merge_key,msg.id,[line])
