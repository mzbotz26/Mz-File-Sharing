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

def detect_type(name):
    name = name.lower()
    if re.search(r"s\d+e\d+|season|episode|ep\d+", name):
        return "series"
    return "movie"

def get_quality(name):
    name = name.lower()
    if "webrip" in name: return "WEBRip"
    if "web-dl" in name or "webdl" in name: return "WEB-DL"
    if "hdrip" in name: return "HDRip"
    if "cam" in name: return "CAM"
    if "hdtc" in name: return "HDTC"
    if "prehd" in name: return "PreHD"
    return "HDRip"

def get_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    name = name.lower()
    if "x265" in name or "hevc" in name:
        return "x265"
    return "x264"


# ---------------- TMDB ----------------

def tmdb_search(title, content_type):
    t = "tv" if content_type == "series" else "movie"

    r = requests.get(
        f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if r.get("results"):
        d = r["results"][0]
        imdb = d.get("vote_average","N/A")
        try: imdb = round(float(imdb),1)
        except: pass

        year = d.get("first_air_date" if t=="tv" else "release_date","")[:4]
        return d.get("poster_path"), imdb, year

    return None,"N/A",""


# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    file_name = message.document.file_name if message.document else message.video.file_name
    name = clean(file_name)

    content_type = detect_type(name)

    title = re.sub(
        r"\(.*?\)|\d{3,4}p.*|s\d+e\d+.*|season.*",
        "",
        name,
        flags=re.I
    ).strip()

    quality = get_quality(name)
    res = get_resolution(name)
    codec = get_codec(name)

    # ✅ FINAL LINK FORMAT (Start.py compatible)
    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year = tmdb_search(title, content_type)

    tag = "Series" if content_type == "series" else "Movie"

    line = f"📁 {res} | {codec}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(title)

    # ---------- UPDATE EXISTING POST ----------
    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(title, eps)

        text = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10

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

{line}

Join Our Channel ♥️
👉 https://t.me/MzMoviiez
"""

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
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
