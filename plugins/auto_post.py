import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    r = requests.get(
        f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d = r["results"][0]
    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = d.get("release_date","")[:4]
    story = d.get("overview","N/A")
    lang = d.get("original_language","").upper()
    return poster, imdb, year, story, lang

# ---------------- HELPERS ----------------

def make_db_key(title, year):
    return re.sub(r'[^a-z0-9]', '', f"{title.lower()}{year}")

def clean_title(name):
    name = name.replace("_"," ").replace("."," ")
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    name = re.sub(r'\b(480p|720p|1080p|2160p|x264|x265|hevc|webdl|webrip|hdrip|bluray|brrip|dvdrip|camrip)\b','',name,flags=re.I)
    name = re.sub(r'\s+',' ',name).strip()
    return name.title()

def detect_resolution(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def detect_quality(name):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in name.lower():
            return q.upper()
    return "WEB-DL"

def detect_language(name):
    langs=[]
    for k,v in {
        "hindi":"Hindi","telugu":"Telugu","tamil":"Tamil",
        "malayalam":"Malayalam","kannada":"Kannada",
        "marathi":"Marathi","gujarati":"Gujarati",
        "dual":"Dual Audio","multi":"Multi Audio"
    }.items():
        if k in name.lower():
            langs.append(v)
    return " ".join(sorted(set(langs))) if langs else "Unknown"

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name
    size = media.file_size

    title = clean_title(fname)
    poster, imdb, year, story, lang2 = tmdb_fetch(title)

    show_year = year or "N/A"
    db_title = make_db_key(title, show_year)

    res = detect_resolution(fname)
    quality = detect_quality(fname)
    lang = detect_language(fname)

    size_mb = round(size/1024/1024,2)
    size_text = f"{size_mb} MB" if size_mb < 1024 else f"{round(size_mb/1024,2)} GB"

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    line = f"➤ {res} ➪ <a href='{link}'>Download Here</a> ({size_text})"

    old = await get_series(db_title)

    head = f"🔥 Title :- {title} ({show_year})"
    quality_line = "🎉 Quality :- 480p, 720p, 1080p ["+quality+"]"
    audio_line = f"🔊 Audio :- {lang}"

    base_text = f"""{head}

{quality_line}

💥 Links 🔗

"""

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        text = base_text
        for e in eps:
            text += e + "\n"

        text += f"""

{audio_line}

💪 Powered By : https://t.me/MzMoviiez
"""

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text = base_text + line + f"""

{audio_line}

💪 Powered By : https://t.me/MzMoviiez
"""

    if poster:
        msg = await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await client.send_message(POST_CHANNEL, text, parse_mode=ParseMode.HTML)

    await save_series(db_title, msg.id, [line])
