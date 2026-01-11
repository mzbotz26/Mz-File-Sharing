import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- CLEAN ----------------

def clean(name):
    return re.sub(r"\s+", " ", name.replace(".", " ").replace("_"," ")).strip()

def normalize_title(name):
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"(480p|720p|1080p|2160p|4k).*","",name)
    name = re.sub(r"x264|x265|hevc|10bit|8bit|aac|ddp.*","",name)
    name = re.sub(r"bluray|brrip|hdrip|webrip|web-dl|webdl|camrip|hdts|hdtc|prehd","",name)
    name = re.sub(r"\d{4}","",name)
    return name.strip().title()

def detect_type(name):
    return "series" if re.search(r"s\d+e\d+|season|episode",name.lower()) else "movie"

def get_res(name):
    if "2160" in name: return "4K"
    if "1080" in name: return "1080p"
    if "720" in name: return "720p"
    if "480" in name: return "480p"
    return "HD"

def get_codec(name):
    return "x265" if "x265" in name.lower() or "hevc" in name.lower() else "x264"

def get_bit(name):
    return "10Bit" if "10bit" in name.lower() else "8Bit"

def get_lang(name):
    n=name.lower()
    if "dual" in n: return "Dual Audio"
    if "multi" in n: return "Multi Audio"
    if "hindi" in n: return "Hindi"
    return "N/A"

# ---------------- TMDB ----------------

def tmdb_fetch(title, t):
    t="tv" if t=="series" else "movie"
    r=requests.get(f"https://api.themoviedb.org/3/search/{t}?api_key={TMDB_API_KEY}&query={title}").json()
    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"

    d=r["results"][0]
    poster=d.get("poster_path")
    imdb=round(float(d.get("vote_average",0)),1) if d.get("vote_average") else "N/A"
    year=(d.get("first_air_date") or d.get("release_date") or "")[:4]
    story=d.get("overview","N/A")
    lang=d.get("original_language","N/A").upper()
    genre="N/A"
    return poster, imdb, year, story, genre, lang

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    name=message.document.file_name if message.document else message.video.file_name
    raw=clean(name)

    title=normalize_title(raw)
    db_title=title.lower()

    res=get_res(raw)
    codec=get_codec(raw)
    bit=get_bit(raw)
    lang_auto=get_lang(raw)

    typ=detect_type(raw)

    code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    poster,imdb,year,story,genre,lang=tmdb_fetch(title,typ)

    tag="Series" if typ=="series" else "Movie"

    line=f"📁 {res} | {codec} | {bit}\n╰─➤ <a href='{link}'>Click Here</a>"

    old=await get_series(db_title)

    text=f"""🎬 {title} ({year}) Hindi [{tag}]

⭐ IMDb: {imdb}/10
🎭 Genre: {genre}
🌐 Language: {lang_auto if lang_auto!="N/A" else lang}

📖 Story:
{story}

"""

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)
            await update_series_episodes(db_title,eps)

        for e in eps:
            text+=e+"\n\n"

        text+="Join Our Channel ❤️\n👉 https://t.me/MzMoviiez"

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    caption=text+line+"\n\nJoin Our Channel ❤️\n👉 https://t.me/MzMoviiez"

    if poster:
        msg=await client.send_photo(POST_CHANNEL,f"https://image.tmdb.org/t/p/w500{poster}",caption=caption,parse_mode=ParseMode.HTML)
    else:
        msg=await client.send_message(POST_CHANNEL,caption,parse_mode=ParseMode.HTML)

    await save_series(db_title,msg.id,[line])
