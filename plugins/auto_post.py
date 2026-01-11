import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ================= CLEAN =================

def clean(name):
    return name.replace(".", " ").replace("_", " ").replace("[", "").replace("]", "")

def normalize_title(name):
    name = name.lower()

    name = re.sub(r"s\d+e\d+.*", "", name)
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\d{4}", "", name)
    name = re.sub(r"amzn|nf|dsnp|hotstar|prime", "", name)
    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc", "", name)
    name = re.sub(r"x264|x265|hevc|h264|h265", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip().title()

# ================= DETECT =================

def get_quality(n):
    n=n.lower()
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n: return q.upper()
    return "HDRip"

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def get_bit(n):
    if "10bit" in n.lower(): return "10Bit"
    return "8Bit"

def get_lang(n):
    n=n.lower()
    if "dual" in n: return "Dual Audio"
    if "multi" in n: return "Multi Audio"
    if "hindi" in n: return "Hindi"
    if "telugu" in n: return "Telugu"
    if "tamil" in n: return "Tamil"
    if "english" in n: return "English"
    return "EN"

# ================= TMDB =================

def tmdb_fetch(title):

    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(float(d.get("vote_average",0)),1)
    year = d.get("release_date","")[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","N/A").upper()

    return poster, imdb, year, story, "N/A", lang

# ================= AUTO POST =================

@Bot.on_message(filters.chat(CHANNEL_ID) & (filters.document | filters.video))
async def auto_post(client, message):

    fname = message.document.file_name if message.document else message.video.file_name
    raw = clean(fname)

    title = normalize_title(raw)
    db_title = title.lower().strip()   # 🔥 VERY IMPORTANT

    quality = get_quality(raw)
    res = get_resolution(raw)
    codec = get_codec(raw)
    bit = get_bit(raw)
    lang2 = get_lang(raw)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title)

    line = f"📁 {res} | {codec} | {bit}\n╰─➤ <a href='{link}'>Click Here</a>"

    old = await get_series(db_title)

    header = f"""🎬 {title} ({year}) {quality} [Movie]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang2}

📖 Story:
{story}

"""

    # -------- MERGE --------
    if old:
        eps = old["episodes"]

        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        text = header
        for e in eps:
            text += e + "\n\n"

        text += "Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        return

    # -------- FIRST POST --------

    text = header + line + "\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(
            POST_CHANNEL,
            text,
            parse_mode=ParseMode.HTML
        )

    await save_series(db_title, msg.id, [line])
