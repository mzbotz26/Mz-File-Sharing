import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes


# ================= CLEANERS =================

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()

    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"s\d+e\d+|season\s*\d+|episode\s*\d+", "", name)
    name = re.sub(r"amzn|netflix|nf|dsnp|hotstar|prime", "", name)
    name = re.sub(r"ddp\d+\.\d+", "", name)
    name = re.sub(r"x264|x265|hevc|h\.?264|h\.?265", "", name)
    name = re.sub(r"webrip|web\-dl|webdl|hdrip|bluray|brrip|dvdrip", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip().title()

def detect_type(name):
    if re.search(r"s\d+e\d+|season|episode|ep\d+", name.lower()):
        return "series"
    return "movie"

def get_quality(name):
    name = name.lower()
    if "webrip" in name: return "WEBRip"
    if "web-dl" in name or "webdl" in name: return "WEB-DL"
    if "hdrip" in name: return "HDRip"
    if "cam" in name: return "CAM"
    if "hdtc" in name: return "HDTC"
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


# ================= TMDB =================

def tmdb_fetch(title, content_type):
    t = "tv" if content_type == "series" else "movie"

    try:
        r = requests.get(
            f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}",
            timeout=10
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A",""

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A",""

    d = r["results"][0]

    imdb = d.get("vote_average","N/A")
    try: imdb = round(float(imdb),1)
    except: pass

    year = d.get("first_air_date" if t=="tv" else "release_date","")[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    genre = "N/A"
    if d.get("genre_ids"):
        genre = " / ".join(str(g) for g in d["genre_ids"])

    return d.get("poster_path"), imdb, year, story, genre, lang


# ================= AUTO POST =================

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    file_name = message.document.file_name if message.document else message.video.file_name
    raw = clean(file_name)

    content_type = detect_type(raw)
    title = normalize_title(raw)
    db_title = title.lower()

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title, content_type)

    tag = "Series" if content_type=="series" else "Movie"

    line = f"📁 {res} | {codec}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(db_title)

    # ================= UPDATE POST =================

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        text = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang}

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

    # ================= FIRST POST =================

    caption = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang}

📖 Story:
{story}

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

    await save_series(db_title, msg.id, [line])
