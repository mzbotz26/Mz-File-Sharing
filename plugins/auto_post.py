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

# ---------------- CLEAN TITLE ----------------

def clean_title(raw):
    raw = raw.replace(".", " ").replace("_", " ")
    raw = re.sub(r"\d{4}", "", raw)
    raw = re.sub(r"\d{3,4}p", "", raw, flags=re.I)
    raw = re.sub(
        r"\b(hindi|telugu|tamil|malayalam|marathi|dual|audio|uncut|south|web|webdl|webrip|bluray|hdrip|brrip|x264|x265|hevc|dd|ddp|aac|kbps|mk|mkv|mp4|proper)\b",
        "",
        raw,
        flags=re.I
    )
    raw = re.sub(r"\b\d+\b","", raw)
    raw = re.sub(r"[^a-zA-Z0-9 ]","", raw)
    raw = re.sub(r"\s+"," ", raw).strip()
    return raw.title()

def merge_key_title(title):
    return re.sub(r"[^a-z0-9]","", title.lower())

# ---------------- UTILS ----------------

def bytes_to_size(size):
    mb = round(size / 1024 / 1024, 2)
    return f"{mb} MB" if mb < 1024 else f"{round(mb/1024,2)} GB"

def detect_source(name):
    for s in ["bluray","brrip","webdl","webrip","hdrip","cam","hdtc","prehd"]:
        if s in name.lower():
            return s.upper()
    return "WEB-DL"

def detect_languages(name):
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi","korean","japanese","spanish","french"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " / ".join(sorted(set(langs))) if langs else "Unknown"

def detect_quality(res):
    if not res: return ""
    if "2160" in res or "4k" in res.lower(): return "2160p"
    if "1080" in res: return "1080p"
    if "720" in res: return "720p"
    if "480" in res: return "480p"
    return res

def sort_key(x):
    nums = re.findall(r"\d+", x)
    return [int(n) for n in nums] if nums else [0]

# ---------------- IMDb ----------------

def imdb_fetch(title):
    try:
        s = ia.search_movie(title)
        if not s:
            return None,None,None,None,None

        m = ia.get_movie(s[0].movieID)

        poster = m.get("full-size cover url")
        rating = str(m.get("rating","N/A"))
        year = str(m.get("year","N/A"))
        story = m.get("plot outline","N/A")
        genres = " / ".join(m.get("genres",[]))

        return poster,rating,year,story,genres if genres else None
    except:
        return None,None,None,None,None

# ---------------- TMDB BACKUP ----------------

def tmdb_fetch(title, is_series=False):
    try:
        url = "tv" if is_series else "movie"
        s = requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()

        if not s.get("results"):
            return None,None,None,None,None

        m = s["results"][0]

        d = requests.get(
            f"https://api.themoviedb.org/3/{url}/{m['id']}?api_key={TMDB_API_KEY}"
        ).json()

        poster = "https://image.tmdb.org/t/p/w500"+d.get("poster_path","") if d.get("poster_path") else None
        rating = str(d.get("vote_average","N/A"))
        year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
        story = d.get("overview","N/A")
        genres = " / ".join([g["name"] for g in d.get("genres",[])])

        return poster,rating,year,story,genres if genres else None
    except:
        return None,None,None,None,None

# ---------------- MULTI LANGUAGE STORY ----------------

def tmdb_story_multi(title, is_series=False):
    try:
        url = "tv" if is_series else "movie"
        s = requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()

        if not s.get("results"):
            return None, None

        mid = s["results"][0]["id"]

        en = requests.get(
            f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}&language=en-US"
        ).json()

        hi = requests.get(
            f"https://api.themoviedb.org/3/{url}/{mid}?api_key={TMDB_API_KEY}&language=hi-IN"
        ).json()

        return en.get("overview"), hi.get("overview")

    except:
        return None, None

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
    parsed_year = parsed.get("year")
    season = parsed.get("season")
    episode = parsed.get("episode")

    is_series = bool(season or episode)

    title = clean_title(raw_title)
    if not title:
        return

    poster,rating,imdb_year,story,genres = imdb_fetch(title)

    if not poster or not genres or not story:
        tposter,trating,tyear,tstory,tgenres = tmdb_fetch(title, is_series)
        poster = poster or tposter
        rating = rating or trating
        imdb_year = imdb_year or tyear
        story = story or tstory
        genres = genres or tgenres

    en_story, hi_story = tmdb_story_multi(title, is_series)

    final_story = ""
    if en_story:
        final_story += f"<b>📕 Story (English):</b>\n{en_story}\n\n"
    if hi_story:
        final_story += f"<b>📕 कहानी (Hindi):</b>\n{hi_story}\n"

    show_year = parsed_year or imdb_year or "N/A"

    merge_key = f"{merge_key_title(title)}_{show_year}"
    if season:
        merge_key += f"_s{season}"

    if merge_key not in locks:
        locks[merge_key] = asyncio.Lock()

    async with locks[merge_key]:

        code = await encode(f"get-{message.id*abs(client.db_channel.id)}")
        link = f"https://t.me/{client.username}?start={code}"

        resolution = detect_quality(parsed.get("resolution",""))
        codec = parsed.get("codec","x264")
        source = detect_source(fname)

        size_text = bytes_to_size(size)

        ep_tag = f"S{season:02d}E{episode:02d}" if season and episode else ""

        line = f"📂 ➤ {ep_tag} {resolution} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

        head = f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres or "N/A"}
<b>⭐️ Rating:</b> {rating or "N/A"}/10
<b>📆 Year:</b> {show_year}

{final_story or "<b>📕 Story:</b> N/A"}

"""

        footer = f"""

<b>🔊 Audio :-</b> {detect_languages(fname)}

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

        old = await get_series(merge_key)

        if old:
            eps = old["episodes"]
            if line not in eps:
                eps.append(line)
                eps.sort(key=sort_key)
                await update_series_episodes(merge_key, eps)

            text = head + "\n".join(eps) + footer

            await client.edit_message_text(
                POST_CHANNEL,
                old["post_id"],
                text,
                parse_mode=ParseMode.HTML
            )
            return

        text = head + line + footer

        if poster:
            msg = await client.send_photo(
                POST_CHANNEL,
                poster,
                caption=text,
                parse_mode=ParseMode.HTML
            )
        else:
            msg = await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

        await save_series(merge_key,msg.id,[line])
