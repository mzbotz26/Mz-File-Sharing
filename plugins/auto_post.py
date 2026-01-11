import re, requests
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

def clean(n):
    return n.replace(".", " ").replace("_", " ")

def normalize_title(n):
    n=n.lower()
    n=re.sub(r"\(.*?\)|\[.*?\]","",n)
    n=re.sub(r"\d{4}","",n)
    n=re.sub(r"webrip|webdl|web-dl|hdrip|bluray|brrip|dvdrip|camrip|prehd|hdtc","",n)
    n=re.sub(r"x264|x265|hevc|h264|h265","",n)
    n=re.sub(r"\d{3,4}p.*","",n)
    return n.strip().title()

def get_res(n):
    if "1080" in n: return "1080p"
    if "720" in n: return "720p"
    if "480" in n: return "480p"
    return "HD"

def get_codec(n):
    if "x265" in n or "hevc" in n: return "x265"
    return "x264"

def tmdb_fetch(title):
    r=requests.get(f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}").json()
    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A","N/A"
    d=r["results"][0]
    return d.get("poster_path"),round(float(d.get("vote_average",0)),1),d.get("release_date","")[:4],d.get("overview","N/A"),"N/A",d.get("original_language","").upper()

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    db_msg = await message.copy(client.db_channel.id)

    fname = db_msg.document.file_name if db_msg.document else db_msg.video.file_name
    raw=clean(fname)

    title=normalize_title(raw)
    db_title=title.lower()

    res=get_res(raw)
    codec=get_codec(raw)

    code=await encode(f"get-{db_msg.id}")
    link=f"https://t.me/{client.username}?start={code}"

    poster,imdb,year,story,genre,lang=tmdb_fetch(title)

    line=f"📁 {res} | {codec}\n╰─➤ <a href='{link}'>Click Here</a>"

    old=await get_series(db_title)

    text=f"""🎬 {title} ({year}) WEB-DL [Movie]

⭐ IMDb: {imdb}/10
🌐 Language: {lang}

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
        text+="Join Our Channel ❤️"
        await client.edit_message_text(POST_CHANNEL,old["post_id"],text,parse_mode=ParseMode.HTML)
        return

    text+=line+"\n\nJoin Our Channel ❤️"

    if poster:
        msg=await client.send_photo(POST_CHANNEL,f"https://image.tmdb.org/t/p/w500{poster}",caption=text,parse_mode=ParseMode.HTML)
    else:
        msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(db_title,msg.id,[line])
