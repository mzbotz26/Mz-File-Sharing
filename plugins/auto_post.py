import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes


# ---------------- HELPERS ----------------

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"webrip|web-dl|webdl|hdrip|bluray|brrip|dvdrip", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def detect_type(name):
    if re.search(r"s\d+e\d+|season|episode|ep\d+", name.lower()):
        return "series"
    return "movie"

def get_quality(name):
    n = name.lower()
    if "webrip" in n: return "WEBRip"
    if "web-dl" in n or "webdl" in n: return "WEB-DL"
    if "hdrip" in n: return "HDRip"
    return "HDRip"

def get_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    if "x265" in name.lower() or "hevc" in name.lower():
        return "x265"
    return "x264"


# ---------------- TMDB ----------------

def tmdb_search(title, content_type):
    t = "tv" if content_type == "series" else "movie"

    url = f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}"
    r = requests.get(url, timeout=10).json()

    if not r.get("results"):
        return None,"N/A","", "N/A", "N/A", "N/A"

    d = r["results"][0]

    imdb = d.get("vote_average","N/A")
    try: imdb = round(float(imdb),1)
    except: pass

    year = d.get("first_air_date" if t=="tv" else "release_date","")[:4]
    poster = d.get("poster_path")
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    # fetch genres
    gid = d.get("id")
    g_url = f"https://api.themoviedb.org/3/{t}/{gid}?api_key={TMDB_API_KEY}"
    gd = requests.get(g_url).json()
    genres = ", ".join([g["name"] for g in gd.get("genres",[])]) or "N/A"

    return poster, imdb, year, story, genres, lang


# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    file_name = message.document.file_name if message.document else message.video.file_name
    raw_name = clean(file_name)

    content_type = detect_type(raw_name)
    title = normalize_title(raw_name)

    quality = get_quality(raw_name)
    res = get_resolution(raw_name)
    codec = get_codec(raw_name)

    code = await encode(f"{client.db_channel.id}:{message.id}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genres, lang = tmdb_search(title, content_type)

    tag = "Series" if content_type=="series" else "Movie"

    line = f"📁 {res} | {codec}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(title)

    # ---------- MERGE ----------
    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(title, eps)

        text = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genres}
🗣 Language: {lang}

📖 Story:
{story}

"""

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

    # ---------- FIRST POST ----------
    caption = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genres}
🗣 Language: {lang}

📖 Story:
{story}

{line}

Join Our Channel ♥️
👉 https://t.me/MzMoviiez
"""

    if poster:
        poster_url = f"https://image.tmdb.org/t/p/w500{poster}"
        msg = await client.send_photo(
            POST_CHANNEL,
            poster_url,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(
            POST_CHANNEL,
            caption,
            parse_mode=ParseMode.HTML
        )

    await save_series(title, msg.id, [line])
