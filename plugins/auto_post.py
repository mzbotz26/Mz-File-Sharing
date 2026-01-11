import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ================= DETECTORS =================

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\b(amzn|nf|dsnp|hotstar|prime)\b", "", name)
    name = re.sub(r"\b(webdl|web-dl|webrip|hdrip|bluray|brrip|dvdrip|cam|hdtc|prehd)\b", "", name)
    name = re.sub(r"\b(x264|x265|hevc|h264|h265)\b", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def detect_type(name):
    if re.search(r"s\d+e\d+|season|episode|ep\d+", name.lower()):
        return "series"
    return "movie"

def get_quality(name):
    name=name.lower()
    if "bluray" in name: return "BluRay"
    if "web-dl" in name or "webdl" in name: return "WEB-DL"
    if "webrip" in name: return "WEBRip"
    if "hdrip" in name: return "HDRip"
    if "cam" in name: return "CAMRip"
    if "hdtc" in name: return "HDTC"
    if "prehd" in name: return "PreHD"
    return "HDRip"

def get_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    name=name.lower()
    if "x265" in name or "hevc" in name: return "x265 HEVC"
    return "x264"

def get_audio(name):
    name=name.lower()
    if "dual" in name: return "Dual Audio"
    if "multi" in name: return "Multi Audio"
    return "Hindi"

def get_bit(name):
    name=name.lower()
    if "10bit" in name: return "10bit"
    return "8bit"

# ================= TMDB =================

def tmdb_fetch(title, ctype):
    t = "tv" if ctype=="series" else "movie"
    r = requests.get(f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}").json()
    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A",""

    d=r["results"][0]
    imdb=round(float(d.get("vote_average",0)),1)
    year=(d.get("release_date") or d.get("first_air_date",""))[:4]
    story=d.get("overview","N/A")
    lang=d.get("original_language","N/A").upper()
    return d.get("poster_path"), imdb, year, story, "N/A", lang

# ================= AUTO POST =================

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video): return

    fname = message.document.file_name if message.document else message.video.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    db_title = title.lower()
    ctype = detect_type(raw)

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    audio = get_audio(raw)
    bit = get_bit(raw)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title, ctype)

    tag = "Series" if ctype=="series" else "Movie"

    line = f"📁 {res} | {codec} | {bit}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(db_title)

    text = f"""🎬 {title} ({year}) {audio} {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang}

📖 Story:
{story}

"""

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        for e in eps: text+=e+"\n\n"
        text+="Join Our Channel ♥️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(POST_CHANNEL, old["post_id"], text, parse_mode=ParseMode.HTML)
        return

    text+=line+"\n\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg=await client.send_photo(POST_CHANNEL, f"https://image.tmdb.org/t/p/w500{poster}", caption=text, parse_mode=ParseMode.HTML)
    else:
        msg=await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, [line])
