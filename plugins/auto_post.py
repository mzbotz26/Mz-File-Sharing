import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN ----------------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)

    remove = [
        "480p","720p","1080p","2160p","4k",
        "x264","x265","hevc","hdrip","webrip","webdl",
        "bluray","dvdrip","camrip","prehd","hdtc",
        "aac","ddp","mkv","mp4",
        "hindi","telugu","tamil","malayalam","marathi",
        "punjabi","gujarati","dual","multi","audio",
        "uncut","south"
    ]

    for w in remove:
        name = re.sub(rf"\b{w}\b","",name,flags=re.I)

    name = re.sub(r"\s+"," ",name)
    return name.strip().title()

def detect_year(name):
    m = re.search(r"(19|20)\d{2}", name)
    return m.group() if m else None

def detect_audio(name):
    langs=[]
    for l in ["hindi","telugu","tamil","malayalam","marathi","punjabi","gujarati","english"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " ".join(sorted(set(langs))) if langs else "Unknown"

def detect_quality(name):
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    if "x265" in name.lower() or "hevc" in name.lower():
        return "x265"
    return "x264"

def detect_season_episode(name):
    s = re.search(r"S(\d+)", name, re.I)
    e = re.search(r"E(\d+)", name, re.I)

    season = f"S{int(s.group(1)):02d}" if s else None
    episode = f"E{int(e.group(1)):02d}" if e else None

    return season, episode

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False):
    media = "tv" if is_series else "movie"
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/{media}?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    rating = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")
    genre = " / ".join([str(x) for x in d.get("genre_ids",[])]) or "N/A"

    return poster, rating, year, story, genre

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    title = clean_title(fname)
    year = detect_year(fname)
    audio = detect_audio(fname)
    quality = detect_quality(fname)
    codec = detect_codec(fname)

    season, episode = detect_season_episode(fname)
    is_series = bool(season)

    poster, rating, tmdb_year, story, genre = tmdb_fetch(title, is_series)
    show_year = year or tmdb_year or "N/A"

    # 🔥 SEASON BASED MERGE KEY
    merge_key = f"{title.lower()}_{show_year}_{season}" if season else f"{title.lower()}_{show_year}"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    ep_tag = f"{season}{episode} | " if season and episode else ""
    line = f"📂 ➤ <b>{ep_tag}{quality} {codec} WEBDL HDRip</b> ➪ <a href='{link}'>Get File</a> ({size_text})"

    season_title = f"{title} {season}" if season else title

    head = f"""<b>🔖 Title: {season_title}</b>
<b>🎬 Genres:</b> {genre}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer = f"""

<b>🔊 Audio :- {audio}</b>

<b>💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a></b>
"""

    old = await get_series(merge_key)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            eps.sort()
            await update_series_episodes(merge_key, eps)

        body = "\n".join(eps)
        text = head + body + footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
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
        msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(merge_key, msg.id, [line])
