import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- UTILS ----------------

def clean_name(name):
    name = name.replace(".", " ").replace("_", " ")
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"\d{3,4}p.*", "", name, flags=re.I)
    name = re.sub(r"x264|x265|hevc|h264|h265","",name,flags=re.I)
    name = re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc","",name,flags=re.I)
    name = re.sub(r"amzn|nf|dsnp|prime|hotstar|zee5|sonyliv","",name,flags=re.I)
    name = re.sub(r"\s+"," ",name)
    return name.strip().title()

def get_resolution(n):
    if "2160" in n: return "4K"
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    return "x265" if "x265" in n.lower() or "hevc" in n.lower() else "x264"

def get_quality(n):
    for q in ["web-dl","webrip","hdrip","bluray","brrip","dvdrip","camrip","prehd","hdtc"]:
        if q in n.lower(): return q.upper()
    return "WEB-DL"

def get_lang(n):
    langs=[]
    for k,v in {
        "hindi":"Hindi","tel":"Telugu","tam":"Tamil","mal":"Malayalam",
        "kan":"Kannada","guj":"Gujarati","mar":"Marathi","pun":"Punjabi",
        "ben":"Bengali","eng":"English"
    }.items():
        if k in n.lower():
            langs.append(v)
    return " ".join(langs) if langs else "Unknown"

def format_size(s):
    if s >= 1024*1024*1024:
        return f"{s/(1024*1024*1024):.2f}GB"
    return f"{s/(1024*1024):.1f}MB"

# ---------------- TMDB ----------------

def tmdb_fetch(title):
    r = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        params={"api_key":TMDB_API_KEY,"query":title}
    ).json()

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d = r["results"][0]

    poster = d.get("poster_path")
    imdb = round(d.get("vote_average",0),1)
    year = d.get("release_date","")[:4]
    story = d.get("overview","N/A")
    genre = " / ".join([str(x) for x in d.get("genre_ids",[])])
    lang = d.get("original_language","").upper()

    return poster, imdb, year, story, genre, lang

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client, message):

    if not (message.document or message.video):
        return

    media = message.document or message.video
    fname = media.file_name

    title = clean_name(fname)

    # 🔥 SAME TITLE ALWAYS = MERGE WORK
    db_title = title.lower()

    quality = get_quality(fname)
    res = get_resolution(fname)
    codec = get_codec(fname)
    langs = get_lang(fname)
    size = format_size(media.file_size)

    code = await encode(f"get-{message.id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={code}"

    poster, imdb, year, story, genre, lang = tmdb_fetch(title)

    line = f"📁 {langs} | {res} | {codec} | {quality}\n╰─➤ <a href='{link}'>Click Here</a> ({size})"

    old = await get_series(db_title)

    text = f"""🎬 {title} ({year})

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {langs}

📖 Story:
{story}

"""

    if old:
        eps = old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title, eps)

        for e in eps:
            text += e + "\n\n"

        text += "Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text += line + "\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

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
