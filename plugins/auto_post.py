import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN TITLE ----------------

def normalize_title(name):
    name = name.lower()

    year = re.findall(r"(19\d{2}|20\d{2})", name)
    year = year[0] if year else ""

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"(19\d{2}|20\d{2})", "", name)

    name = re.sub(r"amzn|nf|dsnp|hotstar|prime|skymovies|katmoviehd|yts|rarbg|mkvcinemas|moviesflix", "", name)
    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name)
    name = re.sub(r"x264|x265|hevc|h264|h265|\d{3,4}p", "", name)

    name = re.sub(r"\s+", " ", name).strip().title()

    if year:
        return f"{name} ({year})"

    return name

# ---------------- DETECT ----------------

def detect_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def detect_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def detect_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower():
            return q.upper()
    return "HDRip"

def detect_language(n):
    langs=[]
    if "hindi" in n.lower(): langs.append("Hindi")
    if "marathi" in n.lower(): langs.append("Marathi")
    if "tamil" in n.lower(): langs.append("Tamil")
    if "telugu" in n.lower(): langs.append("Telugu")
    if "malayalam" in n.lower(): langs.append("Malayalam")
    if "kannada" in n.lower(): langs.append("Kannada")
    if "punjabi" in n.lower(): langs.append("Punjabi")
    if "dual" in n.lower(): langs.append("Dual Audio")
    if "multi" in n.lower(): langs.append("Multi Audio")

    return " ".join(langs) if langs else "Unknown"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]
    return (
        d.get("poster_path"),
        round(d.get("vote_average",0),1),
        d.get("release_date","")[:4],
        d.get("overview","N/A"),
        " / ".join([str(x) for x in d.get("genre_ids",[])]),
        d.get("original_language","N/A").upper()
    )

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    fname = message.document.file_name if message.document else message.video.file_name
    raw = fname

    title = normalize_title(raw)
    db_title = title.lower().strip()

    res = detect_resolution(raw)
    codec = detect_codec(raw)
    quality = detect_quality(raw)
    lang = detect_language(raw)

    size = message.document.file_size if message.document else message.video.file_size
    size_mb = round(size / 1024 / 1024, 2)
    size_txt = f"{size_mb}MB" if size_mb < 1024 else f"{round(size_mb/1024,2)}GB"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, tmdb_lang = tmdb_fetch(title)

    line = f"📁 {lang} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here ({size_txt})</a>"

    old = await get_series(db_title)

    text = f"""🎬 {title}

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang}

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

        text += "Join Our Channel ♥️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text += line + "\n\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

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
