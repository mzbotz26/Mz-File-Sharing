import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, POST_CHANNEL, TMDB_API_KEY
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN ----------------

def clean_name(name):
    name = name.replace(".", " ").replace("_", " ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"s\d+e\d+.*", "", name)
    name = re.sub(r"\d{4}", "", name)

    remove = [
        "webrip","webdl","web-dl","hdrip","bluray","brrip","dvdrip","camrip",
        "prehd","hdtc","x264","x265","hevc","h264","h265","10bit","8bit",
        "amzn","nf","dsnp","prime","hotstar","zee5","sony","mxplayer",
        "480p","720p","1080p","2160p","dual","multi","audio"
    ]

    for r in remove:
        name = name.replace(r,"")

    name = re.sub(r"\s+"," ",name)
    return name.strip().title()

# ---------------- SERIES DETECT ----------------

def detect_series(name):
    m = re.search(r"s(\d{1,2})e(\d{1,3})", name.lower())
    if m:
        return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    return None

# ---------------- DETECT ----------------

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def get_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower(): return q.upper()
    return "WEB-DL"

def get_languages(n):
    langs=[]
    n=n.lower()
    if "hindi" in n: langs.append("Hindi")
    if "marathi" in n: langs.append("Marathi")
    if "tamil" in n: langs.append("Tamil")
    if "telugu" in n: langs.append("Telugu")
    if "kannada" in n: langs.append("Kannada")
    if "malayalam" in n: langs.append("Malayalam")
    if "english" in n: langs.append("English")
    if not langs: langs.append("Unknown")
    return " ".join(langs)

# ---------------- SIZE ----------------

def size_format(size):
    if size >= 1024*1024*1024:
        return f"{round(size/1024/1024/1024,2)}GB"
    return f"{round(size/1024/1024,2)}MB"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    try:
        r=requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}").json()
        if not r.get("results"):
            return None,None,None,None,None,None
        d=r["results"][0]
        return (
            d.get("poster_path"),
            round(d.get("vote_average",0),1),
            d.get("release_date","")[:4],
            d.get("overview","N/A"),
            " / ".join([str(x) for x in d.get("genre_ids",[])]),
            d.get("original_language","N/A").upper()
        )
    except:
        return None,None,None,None,None,None

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    file = message.document or message.video
    raw_name = clean_name(file.file_name)

    title = normalize_title(raw_name)
    db_title = title.lower()

    series_ep = detect_series(raw_name)

    res = get_resolution(raw_name)
    codec = get_codec(raw_name)
    quality = get_quality(raw_name)
    lang = get_languages(raw_name)
    size = size_format(file.file_size)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, tmdb_lang = tmdb_fetch(title)

    display_title = f"{title}"
    if year:
        display_title += f" ({year})"

    if series_ep:
        display_title += f" {series_ep}"

    line = f"📁 {lang} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here</a> ({size})"

    old = await get_series(db_title)

    text = f"""🎬 {display_title}

⭐ IMDb: {imdb if imdb else "N/A"}/10
🎭 Genre: {genre if genre else "N/A"}
🌐 Language: {tmdb_lang if tmdb_lang else lang}

📖 Story:
{story if story else "N/A"}

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
