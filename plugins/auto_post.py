import re, requests
import PTN
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- UTILS ----------------

def clean_title(text):
    text = re.sub(r"[^a-zA-Z0-9_ ]","", text.lower())
    text = re.sub(r"\s+"," ", text).strip()
    return text

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
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi","korean","japanese"]:
        if l in name.lower():
            langs.append(l.capitalize())
    return " / ".join(langs) if langs else "Unknown"

def sort_key(x):
    nums = re.findall(r"\d+", x)
    return [int(n) for n in nums] if nums else [0]

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False):
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

# ---------------- MAIN HANDLER ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    parsed = PTN.parse(fname)

    title = parsed.get("title","").strip()
    year = parsed.get("year")
    season = parsed.get("season")
    episode = parsed.get("episode")

    if not title:
        return

    is_series = bool(season or episode)

    resolution = parsed.get("resolution","")
    codec = parsed.get("codec","x264")
    source = detect_source(fname)
    audio_lang = detect_languages(fname)

    poster,rating,tmdb_year,story,genres = tmdb_fetch(title,is_series)

    show_year = year or tmdb_year or "N/A"

    clean = clean_title(title)

    merge_key = f"{clean}_{show_year}"
    if is_series and season:
        merge_key += f"_s{season}"

    code = await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_text = bytes_to_size(size)

    ep_tag = f"S{season:02d}E{episode:02d}" if season and episode else ""

    line = f"📂 ➤ {ep_tag} {resolution} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    head = f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer = f"""

<b>🔊 Audio :-</b> {audio_lang}

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old = await get_series(merge_key)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            eps.sort(key=sort_key)
            await update_series_episodes(merge_key, eps)

        body = "\n".join(eps)
        text = head + body + footer

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
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(merge_key,msg.id,[line])
