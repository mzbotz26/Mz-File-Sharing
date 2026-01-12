import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series

# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    name = re.sub(r'\b(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webrip|webdl|bluray|dvdrip|camrip|prehd|hdtc|aac|ddp|dd5|224kbps|mkv|mp4|dual|multi|audio|uncut|south)\b','',name,flags=re.I)
    name = re.sub(r'\+',' ',name)
    name = re.sub(r'\s+',' ',name).strip()
    return name.title()

def detect_year(name):
    m = re.search(r'(19|20)\d{2}', name)
    return m.group() if m else None

def detect_audio(name):
    langs=[]
    for l in ["hindi","telugu","tamil","malayalam","marathi","punjabi","gujarati"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " ".join(langs) if langs else "Unknown"

def detect_quality(name):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in name.lower():
            return q.upper()
    return "WEB-DL"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A"

    if not r.get("results"):
        return None,"N/A"

    d = r["results"][0]
    return d.get("poster_path"), (d.get("release_date","")[:4] or "N/A")

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name

    title = clean_title(fname)
    year = detect_year(fname)
    audio = detect_audio(fname)
    quality = detect_quality(fname)

    poster, tmdb_year = tmdb_fetch(title)
    show_year = year or tmdb_year or "N/A"

    db_title = f"{title.lower()}_{show_year}"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    text = f"""🔥 Title :- {title} ({show_year})

🎉 Quality :- 480p, 720p, 1080p [{quality}]

💥 Link 🔗 ➪ <a href="{link}">Download Here</a>

🔊 Audio :- {audio}

💪 Powered By : https://t.me/MzMoviiez
"""

    old = await get_series(db_title)

    # ---------- MERGE ----------
    if old:
        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    # ---------- NEW POST ----------
    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(
            POST_CHANNEL,
            text,
            parse_mode=ParseMode.HTML
        )

    await save_series(db_title, msg.id, [])
