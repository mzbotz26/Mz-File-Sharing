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
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"(480p|720p|1080p|2160p|4k|x264|x265|hevc|hdrip|webrip|webdl|bluray|dvdrip|camrip|prehd|hdtc|aac|ddp|dd5|mkv|mp4|hindi|telugu|tamil|malayalam|marathi|punjabi|dual|multi|audio|south)", "", name, flags=re.I)
    name = re.sub(r"\s+"," ",name)
    return name.strip().title()

def detect_year(name):
    m = re.search(r"(19|20)\d{2}", name)
    return m.group() if m else None

def detect_season_episode(name):
    s = re.search(r"S(\d{1,2})", name, re.I)
    e = re.search(r"E(\d{1,3})", name, re.I)
    return (int(s.group(1)) if s else None, int(e.group(1)) if e else None)

def detect_quality(name):
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_codec(name):
    return "x265" if "x265" in name.lower() or "hevc" in name.lower() else "x264"

def detect_audio(name):
    langs=[]
    for l in ["hindi","telugu","tamil","malayalam","marathi","punjabi","gujarati"]:
        if l in name.lower(): langs.append(l.capitalize())
    return " ".join(langs) if langs else "Unknown"

# ---------------- TMDB ----------------

def tmdb_fetch(title, is_series=False, season=None):
    url = "tv" if is_series else "movie"
    r = requests.get(f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}").json()
    if not r.get("results"): return None,"N/A","N/A","N/A","N/A"
    d = r["results"][0]
    poster = d.get("poster_path")
    rating = round(d.get("vote_average",0),1)
    year = (d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story = d.get("overview","N/A")
    genres = " / ".join([str(g) for g in d.get("genre_ids",[])]) or "N/A"
    return poster, rating, year, story, genres

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    title = clean_title(fname)
    year = detect_year(fname)
    season, episode = detect_season_episode(fname)

    is_series = bool(season or episode)

    quality = detect_quality(fname)
    codec = detect_codec(fname)
    audio = detect_audio(fname)

    poster, rating, tmdb_year, story, genre = tmdb_fetch(title, is_series, season)
    show_year = year or tmdb_year or "N/A"

    if is_series and season:
        merge_key = f"{title.lower()}_{show_year}_s{season}"
        header = f"🔖 **Title:** {title} Season {season}\n🎬 **Genres:** {genre}\n⭐️ **Rating:** {rating}/10\n📆 **Year:** {show_year}\n📕 **Story:** {story}\n\n"
    else:
        merge_key = f"{title.lower()}_{show_year}"
        header = f"🔖 **Title:** {title}\n🎬 **Genres:** {genre}\n⭐️ **Rating:** {rating}/10\n📆 **Year:** {show_year}\n📕 **Story:** {story}\n\n"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    ep_text = f"E{episode:02d} " if episode else ""
    line = f"📂 ➤ {ep_text}{quality} {codec} ➪ <a href='{link}'>Get File</a> ({size_text})"

    footer = f"\n\n🔊 **Audio :-** {audio}\n\n💪 **Powered By : <a href='https://t.me/MzMoviiez'>MzMoviiez</a>**"

    old = await get_series(merge_key)

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            eps.sort()
            await update_series_episodes(merge_key, eps)

        body = "\n".join(eps)
        text = header + body + footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
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
