import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False):
    url = "tv" if is_series else "movie"
    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    genres=[]
    for g in d.get("genre_ids",[]):
        genres.append(str(g))
    genre=" / ".join(genres) if genres else "N/A"

    return poster, imdb, year, story, genre, lang


# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    name = re.sub(r'\[.*?\]|\(.*?\)', '', name)
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r'\b(480p|720p|1080p|2160p|x264|x265|hevc|hdrip|webrip|webdl|bluray|dvdrip|camrip|prehd|hdtc|aac|ddp|mkv|mp4|dual|multi|audio|uncut|south|hindi|telugu|tamil|malayalam|marathi|punjabi|gujarati)\b','',name,flags=re.I)
    name = re.sub(r'\s+',' ',name).strip()
    return name.title()


def detect_year(name):
    m=re.search(r'(19|20)\d{2}',name)
    return m.group() if m else None


def detect_season_episode(name):
    s=re.search(r'S(\d{1,2})',name,re.I)
    e=re.search(r'E(\d{1,3})',name,re.I)
    return s.group().upper() if s else None, e.group().upper() if e else None


def detect_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"


def detect_quality(name):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in name.lower():
            return q.upper()
    return "WEB-DL"


def detect_codec(name):
    return "x265" if "x265" in name.lower() or "hevc" in name.lower() else "x264"


def detect_audio(name):
    langs=[]
    if "hindi" in name.lower(): langs.append("Hindi")
    if "telugu" in name.lower(): langs.append("Telugu")
    if "tamil" in name.lower(): langs.append("Tamil")
    if "marathi" in name.lower(): langs.append("Marathi")
    if "gujarati" in name.lower(): langs.append("Gujarati")
    if "punjabi" in name.lower(): langs.append("Punjabi")
    return " ".join(langs) if langs else "Unknown"


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

    season, episode = detect_season_episode(fname)
    is_series = bool(season or episode)

    db_title = title.lower().strip()

    res = detect_resolution(fname)
    quality = detect_quality(fname)
    codec = detect_codec(fname)
    audio = detect_audio(fname)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    poster, imdb, y, story, genre, lang2 = tmdb_fetch(title, is_series)

    show_year = year or y or "N/A"

    head = f"🔥 Title :- {title} ({show_year})"

    if is_series:
        head += f" {season or ''} {episode or ''}"

    batch_link = f"<a href='{link}'>Download Here</a>"

    text = f"""{head}

🎉 Quality :- 480p, 720p, 1080p [{quality}]

💥 Link 🔗 ➪ {batch_link}

🔊 Audio :- {audio}

💪 Powered By : https://t.me/MzMoviiez
"""

    old = await get_series(db_title)

    if old:
        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, ["BATCH"])
