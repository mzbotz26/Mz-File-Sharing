import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- MAP ----------------

GENRE_MAP = {
28:"Action",12:"Adventure",16:"Animation",35:"Comedy",80:"Crime",
99:"Documentary",18:"Drama",10751:"Family",14:"Fantasy",
36:"History",27:"Horror",10402:"Music",9648:"Mystery",
10749:"Romance",878:"Sci-Fi",53:"Thriller",10752:"War",37:"Western"
}

LANG_MAP = {
"hindi":"Hindi","hin":"Hindi","guj":"Gujarati","gujarati":"Gujarati",
"tam":"Tamil","tamil":"Tamil","tel":"Telugu","mal":"Malayalam",
"kan":"Kannada","eng":"English","english":"English","mar":"Marathi",
"pun":"Punjabi","ben":"Bengali","urd":"Urdu"
}

# ---------------- CLEAN ----------------

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"s\d+e\d+.*","",name)
    name = re.sub(r"\(.*?\)|\[.*?\]","",name)
    name = re.sub(r"\d{4}","",name)
    name = re.sub(r"amzn|nf|dsnp|prime|hotstar|webrip|webdl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc|x264|x265|hevc","",name)
    name = re.sub(r"\s+"," ",name)
    return name.strip().title()

# ---------------- DETECT ----------------

def is_series(name):
    return bool(re.search(r"s\d+e\d+|season\s*\d+", name.lower()))

def get_season_episode(name):
    m = re.search(r"s(\d+)e(\d+)", name.lower())
    if m:
        return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"
    return ""

def get_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower(): return q.upper()
    return "WEB-DL"

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    return "x265" if "x265" in n.lower() or "hevc" in n.lower() else "x264"

def get_languages(n):
    found=[]
    for k,v in LANG_MAP.items():
        if k in n.lower():
            found.append(v)
    return " ".join(sorted(set(found))) if found else "Unknown"

def format_size(size):
    if size >= 1024*1024*1024:
        return f"{size/(1024*1024*1024):.2f}GB"
    return f"{size/(1024*1024):.1f}MB"

# ---------------- TMDB ----------------

def tmdb_fetch(title, series=False):
    url = "tv" if series else "movie"
    r = requests.get(
        f"https://api.themoviedb.org/3/search/{url}",
        params={"api_key": TMDB_API_KEY, "query": title}
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")
    genre = " / ".join([GENRE_MAP.get(i,"") for i in d.get("genre_ids",[])])
    lang = d.get("original_language","").upper()

    return poster, imdb, year, story, genre, lang

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    series = is_series(raw)
    season_ep = get_season_episode(raw)

    db_title = f"{title} {season_ep}".lower().strip() if series else title.lower().strip()

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    langs = get_languages(raw)
    size = format_size(media.file_size)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title, series)

    header = f"🎬 {title} {season_ep}" if series else f"🎬 {title} ({year})"

    line = f"📁 {langs} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here</a> ({size})"

    old = await get_series(db_title)

    text = f"""{header}

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {langs}

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
