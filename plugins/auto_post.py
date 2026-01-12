import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN ----------------

def clean(name):
    return name.replace(".", " ").replace("_", " ").replace("[","").replace("]","")

def normalize_title(name):
    name = name.lower()

    name = re.sub(r"s\d+e\d+.*", "", name)
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\d{4}", "", name)

    name = re.sub(r"amzn|nf|dsnp|hotstar|prime|skymovies|katmoviehd|yts|rarbg|mkvcinemas|moviesflix", "", name)

    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name)
    name = re.sub(r"x264|x265|hevc|h264|h265", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip().title()

# ---------------- DETECT ----------------

def get_quality(n):
    n = n.lower()
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n:
            return q.upper()
    return "HDRip"

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def get_language(n):
    n = n.lower()
    langs = []

    if "hindi" in n: langs.append("Hindi")
    if "telugu" in n: langs.append("Telugu")
    if "tamil" in n: langs.append("Tamil")
    if "malayalam" in n: langs.append("Malayalam")
    if "kannada" in n: langs.append("Kannada")
    if "marathi" in n: langs.append("Marathi")
    if "punjabi" in n: langs.append("Punjabi")
    if "bengali" in n: langs.append("Bengali")
    if "gujarati" in n: langs.append("Gujarati")
    if "english" in n: langs.append("English")

    if "dual" in n and len(langs) < 2:
        return "Dual Audio"

    if langs:
        return " ".join(langs)

    return "Unknown"

def get_size(message):
    size = 0
    if message.document:
        size = message.document.file_size
    elif message.video:
        size = message.video.file_size

    if size == 0:
        return ""

    gb = size / (1024*1024*1024)
    if gb >= 1:
        return f"{gb:.2f}GB"

    mb = size / (1024*1024)
    return f"{mb:.1f}MB"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = d.get("release_date","")[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    genres=[]
    for g in d.get("genre_ids",[]):
        genres.append(str(g))
    genre=" / ".join(genres) if genres else "N/A"

    return poster, imdb, year, story, genre, lang

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    fname = message.document.file_name if message.document else message.video.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    db_title = title.lower().strip()

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    lang_detect = get_language(raw)
    filesize = get_size(message)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title)

    line = f"📁 {lang_detect} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here</a> ({filesize})"

    old = await get_series(db_title)

    text = f"""🎬 {title} ({year}) {quality} [Movie]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang_detect}

📖 Story:
{story}

"""

    if old:
        eps = old["episodes"]

        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        for e in eps:
            text += e + "\n\n"

        text += "Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text += line + "\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, [line])
