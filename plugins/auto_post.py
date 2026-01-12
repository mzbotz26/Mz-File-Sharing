import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN TITLE ----------------

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"s\d+e\d+.*", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"amzn|nf|dsnp|hotstar|prime|skymovies|katmoviehd", "", name)
    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name)
    name = re.sub(r"x264|x265|hevc|h264|h265", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

# ---------------- DETECT ----------------

def get_quality(n):
    n=n.lower()
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n: return q.upper()
    return "WEB-DL"

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
    n=n.lower()
    langs=[]
    for l in ["hindi","tamil","telugu","malayalam","kannada","punjabi","marathi","gujarati","bengali","english"]:
        if l in n: langs.append(l.title())
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

# ---------------- FILE SIZE ----------------

def size_format(size):
    if not size: return ""
    size=float(size)
    if size >= 1024*1024*1024:
        return f"{size/(1024*1024*1024):.2f}GB"
    else:
        return f"{size/(1024*1024):.1f}MB"

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document if message.document else message.video
    fname = media.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    db_title = title.lower().strip()

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    lang = get_language(raw)
    fsize = size_format(media.file_size)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang2 = tmdb_fetch(title)

    display_lang = lang if lang!="Unknown" else lang2

    line = f"📁 {display_lang} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here</a> ({fsize})"

    old = await get_series(db_title)

    text = f"""🎬 {title} ({year})

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {display_lang}

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
