import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- BASIC CLEAN ----------------

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"(19|20)\d{2}", "", name)

    remove = [
        "480p","720p","1080p","2160p","4k",
        "x264","x265","hevc",
        "hdrip","webrip","webdl","bluray","brrip",
        "dvdrip","camrip","prehd","hdtc",
        "aac","ddp","dd5","mkv","mp4",
        "dual","multi","audio","uncut","south"
    ]

    for w in remove:
        name = re.sub(rf"\b{w}\b","",name,flags=re.I)

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
    if "x265" in name or "hevc" in name: return "x265"
    return "x264"

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdtc","prehd"]:
        if s in name:
            return s.upper()
    return "WEB-DL"

def detect_languages(name):
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi"]:
        if l in name:
            langs.append(l.capitalize())
    return " ".join(langs) if langs else "Unknown"

def detect_season_episode(name):
    s=re.search(r"s(\d{1,2})",name)
    e=re.search(r"e(\d{1,3})",name)
    return s.group(1) if s else None, e.group(1) if e else None

# ---------------- TMDB ----------------

def tmdb_fetch(title,is_series=False,season=None):
    url="tv" if is_series else "movie"
    try:
        r=requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d=r["results"][0]
    poster=d.get("poster_path")
    rating=str(d.get("vote_average","N/A"))
    year=(d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story=d.get("overview","N/A")

    genres=[]
    for g in d.get("genre_ids",[]):
        genres.append(str(g))

    return poster,rating,year,story," / ".join(genres) if genres else "N/A"

# ---------------- SORT EPISODES ----------------

def episode_sort_key(line):
    m=re.search(r"E(\d+)",line)
    return int(m.group(1)) if m else 0

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media=message.document or message.video
    fname=media.file_name.lower()
    size=media.file_size

    title=clean_title(fname)
    year=detect_year(fname)

    res=detect_resolution(fname)
    codec=detect_codec(fname)
    source=detect_source(fname)
    languages=detect_languages(fname)

    season,episode=detect_season_episode(fname)
    is_series=True if season else False

    poster,rating,tmdb_year,story,genres=tmdb_fetch(title,is_series,season)
    show_year=year or tmdb_year or "N/A"

    # ---- MERGE KEY ----
    merge_key=f"{title.lower()}_{show_year}"
    if is_series:
        merge_key=f"{merge_key}_s{season}"

    code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    size_mb=round(size/1024/1024,2)
    size_text=f"{size_mb} MB" if size_mb<1024 else f"{round(size_mb/1024,2)} GB"

    ep_tag=f"S{season}E{episode}" if season and episode else ""

    line=f"📂 ➤ {ep_tag} {res} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    # ---- HEADER ----
    head=f"""<b>🔖 Title:</b> {title}"""

    if is_series:
        head+=f" Season {season}"

    head+=f"""

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer=f"""

<b>🔊 Audio :-</b> {languages}

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old=await get_series(merge_key)

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)

        eps=sorted(eps,key=episode_sort_key)
        await update_series_episodes(merge_key,eps)

        body="\n".join(eps)
        text=head+body+footer

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
