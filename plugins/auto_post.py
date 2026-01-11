import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes


# ---------------- HELPERS ----------------

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\b(hindi|dubbed|dual|audio|hdrip|webrip|webdl|bluray|brrip|dvdrip)\b", "", name)
    name = re.sub(r"\b(480p|720p|1080p|2160p|x264|x265|hevc|10bit|8bit)\b", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def detect_type(name):
    if re.search(r"s\d+e\d+|season|episode|ep\d+", name.lower()):
        return "series"
    return "movie"

def get_quality(name):
    n = name.lower()
    if "bluray" in n: return "BluRay"
    if "webrip" in n: return "WEBRip"
    if "web" in n: return "WEB-DL"
    if "hdrip" in n: return "HDRip"
    if "cam" in n: return "CAMRip"
    if "hdtc" in n: return "HDTC"
    if "prehd" in n: return "PreHD"
    return "HD"

def get_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    n = name.lower()
    if "x265" in n or "hevc" in n: return "HEVC x265"
    return "x264"

def get_audio(name):
    n = name.lower()
    if "dual" in n: return "Dual Audio"
    return "Hindi"

def get_bit(name):
    n = name.lower()
    if "10bit" in n: return "10Bit"
    return "8Bit"


# ---------------- TMDB ----------------

def tmdb_fetch(title, content_type):
    t = "tv" if content_type=="series" else "movie"
    r = requests.get(
        f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]
    imdb = round(float(d.get("vote_average",0)),1)
    year = (d.get("first_air_date") if t=="tv" else d.get("release_date",""))[:4]
    overview = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    return d.get("poster_path"), imdb, year, overview, "N/A", lang


# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    file_name = message.document.file_name if message.document else message.video.file_name
    raw = clean(file_name)

    content_type = detect_type(raw)
    title = normalize_title(raw)
    db_title = title.lower()

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    audio = get_audio(raw)
    bit = get_bit(raw)

    code = await encode(f"get-{client.db_channel.id}-{message.id}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title, content_type)

    tag = "Series" if content_type=="series" else "Movie"

    line = f"📁 {res} | {codec} | {bit}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(db_title)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        text = f"""🎬 {title} ({year}) {audio} {quality} [{tag}]

⭐ IMDb: {imdb}/10
🌐 Language: {lang}

📖 Story:
{story}

"""
        for e in eps:
            text += e + "\n\n"

        text += "Join Our Channel ♥️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(POST_CHANNEL, old["post_id"], text, parse_mode=ParseMode.HTML)
        return

    caption = f"""🎬 {title} ({year}) {audio} {quality} [{tag}]

⭐ IMDb: {imdb}/10
🌐 Language: {lang}

📖 Story:
{story}

{line}

Join Our Channel ♥️
👉 https://t.me/MzMoviiez
"""

    if poster:
        msg = await client.send_photo(POST_CHANNEL, f"https://image.tmdb.org/t/p/w500{poster}", caption=caption, parse_mode=ParseMode.HTML)
    else:
        msg = await client.send_message(POST_CHANNEL, caption, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, [line])
