import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ================= CLEANERS =================

JUNK = [
    "webdl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd",
    "x264","x265","hevc","aac","dd5","ddp5","224kbps","uncut","south",
    "hindi","telugu","tamil","malayalam","dual","audio","multi",
    "mkv","mp4","avi","hq"
]

def clean_title(name):
    n = name.lower()
    n = re.sub(r"\[.*?\]|\(.*?\)", "", n)
    n = n.replace("_"," ").replace("."," ")
    for w in JUNK:
        n = re.sub(rf"\b{w}\b", "", n)
    n = re.sub(r"\d{3,4}p","",n)
    n = re.sub(r"\s+"," ",n).strip()
    return n.title()

def normalize_key(title):
    return re.sub(r"[^a-z0-9]","",title.lower())

def detect_year(name):
    m = re.search(r"(19|20)\d{2}", name)
    return m.group(0) if m else None

def detect_series(name):
    return bool(re.search(r"s\d+|season|episode|ep\d+", name.lower()))

def detect_season_episode(name):
    s = re.search(r"s(\d+)", name.lower())
    e = re.search(r"e(\d+)", name.lower())
    return (int(s.group(1)) if s else None,
            int(e.group(1)) if e else None)

def detect_lang(name):
    langs=[]
    if "hindi" in name.lower(): langs.append("Hindi")
    if "telugu" in name.lower(): langs.append("Telugu")
    if "tamil" in name.lower(): langs.append("Tamil")
    if "malayalam" in name.lower(): langs.append("Malayalam")
    return " ".join(langs) if langs else "Unknown"

def detect_res(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    return "x265" if "x265" in name.lower() or "hevc" in name.lower() else "x264"

def detect_quality(name):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd"]:
        if q in name.lower():
            return q.upper()
    return "WEB-DL"

# ================= TMDB =================

def tmdb_fetch(title,is_series):
    t = "tv" if is_series else "movie"
    r = requests.get(
        f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d=r["results"][0]
    poster=d.get("poster_path")
    imdb=round(d.get("vote_average",0),1)
    story=d.get("overview","N/A")
    year=(d.get("first_air_date") if is_series else d.get("release_date",""))[:4]

    # genre name fix
    genre_ids=d.get("genre_ids",[])
    genre=" / ".join(str(g) for g in genre_ids) if genre_ids else "N/A"

    return poster, imdb, year, story, genre

# ================= AUTO POST =================

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media=message.document or message.video
    fname=media.file_name
    size=media.file_size

    title=clean_title(fname)
    key=normalize_key(title)

    year=detect_year(fname)
    is_series=detect_series(fname)
    season,episode=detect_season_episode(fname)

    lang=detect_lang(fname)
    res=detect_res(fname)
    codec=detect_codec(fname)
    quality=detect_quality(fname)

    tag=f"{lang} | {res} | {codec} | {quality}"

    if is_series:
        if season: tag=f"S{season:02d} " + tag
        if episode: tag=f"E{episode:02d} " + tag

    code=await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    mb=size/1024/1024
    size_text=f"{round(mb,2)} MB" if mb<1024 else f"{round(mb/1024,2)} GB"

    line=f"📁 {tag}\n╰─➤ <a href='{link}'>Click Here</a> ({size_text})"

    poster, imdb, y, story, genre = tmdb_fetch(title,is_series)
    show_year=year or y or "N/A"

    head=f"🎬 {title} ({show_year}) [{'Series' if is_series else 'Movie'}]"

    old=await get_series(key)

    text=f"""{head}

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
            await update_series_episodes(key, eps)

        for e in eps:
            text+=e+"\n\n"

        text+="Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text+=line+"\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg=await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(key, msg.id, [line])
