import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------- CLEAN ----------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)

    remove = [
        "480p","720p","1080p","2160p","4k",
        "x264","x265","hevc","hdrip","webrip","webdl",
        "bluray","dvdrip","camrip","prehd","hdtc",
        "aac","ddp","dd5","mkv","mp4",
        "hindi","telugu","tamil","malayalam","marathi",
        "punjabi","gujarati","dual","multi","audio",
        "uncut","south"
    ]

    for w in remove:
        name = re.sub(rf"\b{w}\b", "", name, flags=re.I)

    name = re.sub(r"\b\d+\b","",name)
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

def detect_resolution(name):
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    if "x265" in name.lower() or "hevc" in name.lower():
        return "x265"
    return "x264"

def detect_quality(name):
    for q in ["webdl","webrip","hdrip","bluray","dvdrip","camrip","prehd","hdtc"]:
        if q in name.lower():
            return q.upper()
    return "WEB-DL"

# ---------- TMDB ----------

def tmdb_fetch(title):
    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    year = d.get("release_date","")[:4]
    rating = round(d.get("vote_average",0),1)
    story = d.get("overview","N/A")

    genres = []
    for g in d.get("genre_ids",[]):
        genres.append(str(g))

    return poster, year, rating, story, "Action / Drama" if genres else "N/A"

# ---------- AUTO POST ----------

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

    poster, tmdb_year, rating, story, genre = tmdb_fetch(title)
    show_year = year or tmdb_year or "N/A"

    merge_key = f"{title.lower().strip()}_{show_year}"

    res = detect_resolution(fname)
    codec = detect_codec(fname)
    quality = detect_quality(fname)

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    line = f"➤ {res} {codec} {quality} HDRip ➪ <a href='{link}'>Get File</a> ({size_text})"

    header = f"""🔖 Title: {title}
🎬 Genres: {genre}
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
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(merge_key, msg.id, [line])
