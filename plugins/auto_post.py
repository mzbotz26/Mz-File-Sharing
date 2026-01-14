import re, requests, asyncio
import PTN
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes
from imdb import Cinemagoer

ia = Cinemagoer()
locks = {}

# ---------------- TITLE CLEAN ----------------

def clean_title(raw):
    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")

    # remove text inside brackets
    raw = re.sub(r"\(.*?\)", "", raw)

    # remove year
    raw = re.sub(r"\b(19|20)\d{2}\b", "", raw)

    # remove quality / source / codec
    raw = re.sub(r"\b(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webdl|webrip|bluray|brrip|hdts|hdtc|cam|prehd|hd)\b", "", raw, flags=re.I)

    # remove audio / tech words including kbps formats
    raw = re.sub(r"\b(hindi|telugu|tamil|malayalam|marathi|dual|audio|dd|ddp|dd5|dd5\.1|aac|dts|\d+kbps|kbps|bps|uncut|south|movie|proper|extended|mk|esub)\b", "", raw, flags=re.I)

    # remove long numbers like 224, 320, 2025 etc
    raw = re.sub(r"\b\d{3,}\b", "", raw)

    # remove trailing single digits
    raw = re.sub(r"\b\d\b", "", raw)

    # remove symbols
    raw = re.sub(r"[^a-zA-Z0-9 ]", "", raw)

    # fix spaces
    raw = re.sub(r"\s+", " ", raw).strip()

    return raw.title()

def merge_key_title(title):
    return re.sub(r"[^a-z0-9]","",title.lower())

# ---------------- UTILS ----------------

def bytes_to_size(size):
    mb = round(size / 1024 / 1024, 2)
    return f"{mb} MB" if mb < 1024 else f"{round(mb/1024,2)} GB"

def detect_quality(res):
    if not res: return ""
    if "2160" in res or "4k" in res.lower(): return "2160p"
    if "1080" in res: return "1080p"
    if "720" in res: return "720p"
    if "480" in res: return "480p"
    return res

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdts","hdtc","prehd"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def sort_key(x):
    order=["480","720","1080","2160"]
    for i,o in enumerate(order):
        if o in x: return i
    return 99

# ---------------- IMDb ----------------

def imdb_fetch(title):
    try:
        s = ia.search_movie(title)
        if not s: return None,None,None,None,None

        m = ia.get_movie(s[0].movieID)

        poster = m.get("full-size cover url")
        rating = str(m.get("rating","N/A"))
        year = str(m.get("year",""))
        story = m.get("plot outline","N/A")
        genres = " / ".join(m.get("genres",[]))

        return poster,rating,year,story,genres
    except:
        return None,None,None,None,None

# ---------------- TMDB BACKUP ----------------

def tmdb_fetch(title, is_series=False, season=None):
    try:
        url = "tv" if is_series else "movie"
        s = requests.get(f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}&language=hi-IN").json()
        if not s.get("results"): return None,None,None,None,None,None

        mid = s["results"][0]["id"]

        if is_series and season:
            d = requests.get(f"https://api.themoviedb.org/3/tv/{mid}/season/{season}?api_key={TMDB_API_KEY}&language=hi-IN").json()
        else:
            d = requests.get(f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}&language=hi-IN").json()

        poster = "https://image.tmdb.org/t/p/w500"+d.get("poster_path","") if d.get("poster_path") else None
        rating = str(d.get("vote_average","N/A"))
        year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
        story = d.get("overview","N/A")
        genres = " / ".join([g["name"] for g in d.get("genres",[])])

        return poster,rating,year,story,genres,mid
    except:
        return None,None,None,None,None,None

# ---------------- MAIN ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    parsed = PTN.parse(fname)

    raw_title = parsed.get("title","")
    season = parsed.get("season")
    episode = parsed.get("episode")

    is_series = bool(season or episode)

    title = clean_title(raw_title)
    if not title:
        return

    poster,rating,year,story,genres = imdb_fetch(title)

    if not poster or not genres or not story:
        tposter,trating,tyear,tstory,tgenres,_ = tmdb_fetch(title,is_series,season)
        poster = poster or tposter
        rating = rating or trating
        year = year or tyear
        story = story or tstory
        genres = genres or tgenres

    # -------- SAFE MERGE KEY --------
    merge_key = merge_key_title(title)
    if year:
        merge_key += f"_{year}"
    if season:
        merge_key += f"_s{season}"

    if merge_key not in locks:
        locks[merge_key]=asyncio.Lock()

    async with locks[merge_key]:

        code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
        link=f"https://t.me/{client.username}?start={code}"

        resolution=detect_quality(parsed.get("resolution",""))
        codec=parsed.get("codec","x264")
        source=detect_source(fname)
        size_text=bytes_to_size(size)

        ep_tag=f"S{season:02d}E{episode:02d} " if season and episode else ""

        line=f"""📂 ➤ {ep_tag}{resolution} {codec} {source}
🔗 ➪ <a href='{link}'>Get File</a> ({size_text})"""

        title_line = f"{title} (Season {season})" if season else title

        head=f"""🔖 Title: {title_line}

🎬 Genres: {genres or "N/A"}
⭐️ Rating: {rating or "N/A"}/10
📆 Year: {year or "N/A"}
📕 Story: {story or "N/A"}

"""

        footer=f"""

💪 Powered By : <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        old=await get_series(merge_key)

        if old:
            eps=old["episodes"]
            if line not in eps:
                eps.append(line)
                eps.sort(key=sort_key)
                await update_series_episodes(merge_key,eps)

            text=head+"\n\n".join(eps)+footer

            await client.edit_message_text(
                POST_CHANNEL,
                old["post_id"],
                text,
                parse_mode=ParseMode.HTML
            )
            return

        text=head+line+footer

        if poster:
            msg=await client.send_photo(POST_CHANNEL,poster,caption=text,parse_mode=ParseMode.HTML)
        else:
            msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

        await save_series(merge_key,msg.id,[line])
