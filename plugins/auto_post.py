import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN TITLE ----------------

def clean_title(name):
    name = name.lower()
    name = name.replace("_"," ").replace("."," ")

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)

    remove_words = [
        "480p","720p","1080p","2160p","4k",
        "x264","x265","hevc","hdrip","webrip","webdl","web-dl",
        "bluray","brrip","dvdrip","camrip","prehd","hdtc",
        "aac","ddp","dd5","mkv","mp4","h264","h 264",
        "dual","multi","audio","uncut","south",
        "hindi","english","telugu","tamil","malayalam","marathi"
    ]

    for w in remove_words:
        name = re.sub(rf"\b{w}\b","",name)

    name = re.sub(r"\b\d+\b","",name)
    name = re.sub(r"\s+"," ",name)

    return name.strip().title()

# ---------------- DETECT ----------------

def detect_year(name):
    m=re.search(r"(19|20)\d{2}",name)
    return m.group() if m else None

def detect_resolution(name):
    if "2160" in name: return "2160p"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    return "x265" if "x265" in name or "hevc" in name else "x264"

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdtc"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def detect_languages(name):
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " ".join(langs) if langs else "Unknown"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    try:
        r=requests.get(
            f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d=r["results"][0]
    return (
        d.get("poster_path"),
        str(d.get("vote_average","N/A")),
        d.get("release_date","")[:4],
        d.get("overview","N/A"),
        " / ".join([str(g) for g in d.get("genre_ids",[])]) or "N/A"
    )

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media=message.document or message.video
    fname=media.file_name
    size=media.file_size

    title=clean_title(fname)
    year=detect_year(fname)

    res=detect_resolution(fname)
    codec=detect_codec(fname)
    source=detect_source(fname)
    langs=detect_languages(fname)

    poster,rating,tmdb_year,story,genres=tmdb_fetch(title)

    show_year=year or tmdb_year or "N/A"

    merge_key=f"{title.lower()}_{show_year}"

    code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    size_mb=round(size/1024/1024,2)
    size_text=f"{size_mb} MB" if size_mb<1024 else f"{round(size_mb/1024,2)} GB"

    line=f"📂 ➤ {res} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    head=f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer=f"""

<b>🔊 Audio :-</b> {langs}

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old=await get_series(merge_key)

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(merge_key,eps)

        text=head+"\n".join(sorted(eps))+footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text=head+line+footer

    if poster:
        msg=await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(merge_key,msg.id,[line])
