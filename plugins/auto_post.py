import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\[.*?\]|\(.*?\)", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name, flags=re.I)
    name = re.sub(r"x264|x265|hevc|h264|h265", "", name, flags=re.I)
    name = re.sub(r"web.?dl|webrip|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

# ---------------- DETECT ----------------

def detect_series(name):
    return bool(re.search(r"s\d+e\d+|season|episode", name.lower()))

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    return "x265" if "x265" in n.lower() or "hevc" in n.lower() else "x264"

def get_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower():
            return q.upper()
    return "WEB-DL"

LANG_MAP = {
    "hindi":"Hindi","marathi":"Marathi","tamil":"Tamil","telugu":"Telugu",
    "malayalam":"Malayalam","kannada":"Kannada","punjabi":"Punjabi",
    "dual":"Dual Audio","multi":"Multi Audio"
}

def detect_lang(n):
    langs=[]
    for k,v in LANG_MAP.items():
        if k in n.lower():
            langs.append(v)
    return " ".join(sorted(set(langs))) if langs else "Unknown"

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False):
    url = "tv" if is_series else "movie"
    r = requests.get(
        f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d = r["results"][0]
    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")

    genre="N/A"
    if d.get("genre_ids"):
        genre=" / ".join([str(x) for x in d["genre_ids"]])

    return poster, imdb, year, story, genre

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    is_series = detect_series(fname)
    title = clean_title(fname)
    db_title = title.lower().strip()

    lang = detect_lang(fname)
    res = get_resolution(fname)
    codec = get_codec(fname)
    quality = get_quality(fname)

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    line = f"📁 {lang} | {res} | {codec}\n╰─➤ <a href='{link}'>Click Here</a> ({size_text})"

    poster, imdb, year, story, genre = tmdb_fetch(title, is_series)

    head = f"🎬 {title}"
    if year: head += f" ({year})"
    head += " [Series]" if is_series else " [Movie]"

    old = await get_series(db_title)

    text = f"""{head}

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}

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
