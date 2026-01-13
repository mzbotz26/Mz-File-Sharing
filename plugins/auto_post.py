import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)

    remove = [
        "480p","720p","1080p","2160p","4k",
        "x264","x265","hevc",
        "hdrip","webrip","webdl","web-dl",
        "bluray","brrip","dvdrip","camrip","prehd","hdtc",
        "aac","ddp","dd5","224kbps",
        "mkv","mp4",
        "hindi","telugu","tamil","malayalam","marathi",
        "punjabi","gujarati","dual","multi","audio",
        "uncut","south"
    ]

    for w in remove:
        name = re.sub(rf"\b{w}\b", "", name, flags=re.I)

    name = re.sub(r"\b\d+\b","",name)
    name = re.sub(r"\+"," ",name)
    name = re.sub(r"\s+"," ",name)

    return name.strip().title()

def detect_year(name):
    m = re.search(r"(19|20)\d{2}", name)
    return m.group() if m else None

def detect_audio(name):
    langs=[]
    for l in ["hindi","telugu","tamil","malayalam","marathi","punjabi","gujarati"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " ".join(langs) if langs else "Unknown"

def detect_quality(name):
    name=name.lower()
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    if "x265" in name or "hevc" in name: return "x265"
    return "x264"

def detect_source(name):
    for s in ["webdl","web-dl","webrip","hdrip","bluray","brrip","dvdrip","hdtc","camrip"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A"

    d = r["results"][0]
    poster = d.get("poster_path")
    year = d.get("release_date","")[:4]
    rating = round(d.get("vote_average",0),1)
    story = d.get("overview","N/A")
    return poster, year, rating, story

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
    source = detect_source(fname)

    poster, tmdb_year, rating, story = tmdb_fetch(title)
    show_year = year or tmdb_year or "N/A"

    # 🔥 MERGE KEY (MOST IMPORTANT FIX)
    merge_key = f"{title.lower()}_{show_year}".strip()

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    line = f"➤ {quality} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    header = f"""🔖 Title: {title}
🎬 Genres: N/A
⭐️ Rating: {rating}/10
📆 Year: {show_year}
📕 Story: {story}

"""

    footer = f"""

🔊 Audio :- {audio}

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old = await get_series(merge_key)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(merge_key, eps)

        body = "\n".join(eps)
        text = header + body + footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text = header + line + footer

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            TMDB_IMG + poster,
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(
            POST_CHANNEL,
            text,
            parse_mode=ParseMode.HTML
        )

    await save_series(merge_key, msg.id, [line])
