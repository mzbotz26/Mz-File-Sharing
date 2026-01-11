import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ================= DETECTION =================

def clean(name):
    return name.replace(".", " ").replace("_", " ")

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"s\d+e\d+.*|season.*|episode.*", "", name)
    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|x264|x265|hevc|10bit|8bit","",name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()

def detect_type(name):
    return "series" if re.search(r"s\d+e\d+|season|episode|ep\d+", name.lower()) else "movie"

def get_resolution(name):
    if "2160" in name: return "2160p"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    if "x265" in name.lower() or "hevc" in name.lower(): return "HEVC x265"
    return "x264"

def get_bit(name):
    if "10bit" in name.lower(): return "10Bit"
    if "8bit" in name.lower(): return "8Bit"
    return ""

def get_quality(name):
    n = name.lower()
    if "bluray" in n or "brrip" in n: return "BluRay"
    if "web-dl" in n or "webdl" in n: return "WEB-DL"
    if "webrip" in n: return "WEBRip"
    if "hdrip" in n: return "HDRip"
    if "cam" in n: return "CAMRip"
    if "prehd" in n: return "PreHD"
    if "hdtc" in n: return "HDTC"
    return "HD"

def get_language(name):
    langs=[]
    n=name.lower()
    if "hindi" in n: langs.append("Hindi")
    if "english" in n or "eng" in n: langs.append("English")
    if "tamil" in n: langs.append("Tamil")
    if "telugu" in n: langs.append("Telugu")
    if "malayalam" in n: langs.append("Malayalam")
    if "marathi" in n: langs.append("Marathi")
    if "bengali" in n: langs.append("Bengali")

    if "dual" in n and len(langs)>=2:
        return f"Dual Audio ({langs[0]}/{langs[1]})"
    if langs:
        return "/".join(langs)
    return "Unknown"

# ================= TMDB FULL DETAILS =================

def tmdb_fetch(title, content_type):
    t = "tv" if content_type=="series" else "movie"

    r = requests.get(
        f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    imdb = d.get("vote_average","N/A")
    try: imdb = round(float(imdb),1)
    except: pass

    year = d.get("first_air_date" if t=="tv" else "release_date","")[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","").upper()
    genre = "N/A"

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
    key = title.lower()

    res = get_resolution(raw)
    codec = get_codec(raw)
    bit = get_bit(raw)
    quality = get_quality(raw)
    language = get_language(raw)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, tmdb_lang = tmdb_fetch(title, content_type)

    tag = "Series" if content_type=="series" else "Movie"

    line = f"📁 {res} | {codec} {bit}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(key)

    header = f"""🎬 {title} ({year}) Hindi {quality} [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {language}

📖 Story:
{story}

"""

    # -------- MERGE ----------
    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(key, eps)

        text = header
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

    # -------- FIRST POST ----------
    caption = header + line + "\n\nJoin Our Channel ♥️\n👉 https://t.me/MzMoviiez"

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

    await save_series(key, msg.id, [line])
