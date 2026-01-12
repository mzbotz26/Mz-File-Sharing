import re, requests, PTN
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False):
    url = "tv" if is_series else "movie"
    r = requests.get(
        f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    genres=[]
    for gid in d.get("genre_ids",[]):
        genres.append(str(gid))
    genre=" / ".join(genres) if genres else "N/A"

    return poster, imdb, year, story, genre, lang

# ---------------- DETECT ----------------

LANG_MAP = {
    "hindi":"Hindi","hin":"Hindi",
    "english":"English","eng":"English",
    "telugu":"Telugu","tam":"Tamil","tamil":"Tamil",
    "malayalam":"Malayalam","kan":"Kannada","marathi":"Marathi",
    "punjabi":"Punjabi","gujarati":"Gujarati",
    "dual":"Dual Audio","multi":"Multi Audio"
}

def detect_language(name):
    langs=[]
    n=name.lower()
    for k,v in LANG_MAP.items():
        if k in n:
            langs.append(v)
    return " ".join(sorted(set(langs))) if langs else "Unknown"

def detect_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower():
            return q.upper()
    return "WEB-DL"

def detect_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def detect_codec(n):
    if "x265" in n.lower() or "hevc" in n.lower(): return "x265"
    return "x264"

# ---------------- TITLE PARSER ----------------

def parse_filename(name):
    clean = name.replace("_"," ").replace("."," ")
    clean = re.sub(r"\[.*?\]|\(.*?\)", "", clean)
    parsed = PTN.parse(clean)

    title = parsed.get("title","").strip()
    year = parsed.get("year")
    season = parsed.get("season")
    episode = parsed.get("episode")

    is_series = bool(season or episode)

    return title, year, season, episode, is_series

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    title, year, season, episode, is_series = parse_filename(fname)

    if not title:
        return

    db_title = title.lower().strip()

    lang = detect_language(fname)
    quality = detect_quality(fname)
    res = detect_resolution(fname)
    codec = detect_codec(fname)

    tag = f"{lang} | {res} | {codec} | {quality}"

    if is_series:
        se = f"S{season:02d}" if season else ""
        ep = f"E{episode:02d}" if isinstance(episode,int) else ""
        tag = f"{se}{ep} | " + tag

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb}MB" if size_mb < 1024 else f"{round(size_mb/1024,2)}GB"

    line = f"📁 {tag}\n╰─➤ <a href='{link}'>Click Here</a> ({size_text})"

    poster, imdb, y, story, genre, lang2 = tmdb_fetch(title, is_series)

    show_year = year or y or "N/A"

    head = f"🎬 {title} ({show_year})"
    head += " [Series]" if is_series else " [Movie]"

    old = await get_series(db_title)

    text = f"""{head}

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
