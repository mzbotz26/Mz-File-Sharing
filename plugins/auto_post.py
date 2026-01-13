import re, requests, PTN
from pyrogram import filters
from pyrogram.enums import ParseMode
from bot import Bot
from config import CHANNEL_ID, TMDB_API_KEY, POST_CHANNEL
from helper_func import encode
from database.database import get_series, save_series, update_series_episodes

# ---------------- PARSER ENGINE ----------------

def parse_filename(name):

    clean = name.replace("_"," ").replace("."," ")
    clean = re.sub(r"(?:www\.)?\S+\.(?:com|org|net|xyz|me|io|in|cc|biz|world|info|club|mobi|press|top|site|tech|online|store|live)\b","",clean,flags=re.I)
    clean = re.sub(r"@[a-zA-Z0-9_]+","",clean)

    data = PTN.parse(clean)

    title = data.get("title","").strip()
    year = str(data.get("year","")).strip() or None
    season = data.get("season")
    episode = data.get("episode")

    res = data.get("resolution","HD")
    codec = data.get("codec","x264")
    source = data.get("source","WEB-DL").upper()

    return title, year, season, episode, res, codec, source

# ---------------- AUDIO ----------------

def detect_audio(name):
    name=name.lower()
    langs=[]
    for l in ["hindi","english","telugu","tamil","malayalam","marathi","punjabi","korean","japanese","french","spanish"]:
        if l in name:
            langs.append(l.capitalize())
    if not langs:
        langs=["Unknown"]

    if "multi" in name:
        return "Multi Audio"," ".join(langs)
    if "dual" in name:
        return "Dual Audio"," ".join(langs)
    return "Single Audio"," ".join(langs)

# ---------------- TMDB ----------------

def tmdb_fetch(title,is_series=False):
    url="tv" if is_series else "movie"
    try:
        r=requests.get(
            f"https://api.themoviedb.org/3/search/{url}?api_key={TMDB_API_KEY}&query={title}"
        ).json()
    except:
        return None,"N/A","N/A","N/A","N/A"

    if not r.get("results"):
        return None,"N/A","N/A","N/A","N/A"

    d=r["results"][0]
    poster=d.get("poster_path")
    rating=str(d.get("vote_average","N/A"))
    year=(d.get("first_air_date") if is_series else d.get("release_date",""))[:4]
    story=d.get("overview","N/A")

    genres=[]
    for g in d.get("genre_ids",[]):
        genres.append(str(g))

    return poster,rating,year,story," / ".join(genres) if genres else "N/A"

# ---------------- AUTO POST ----------------

@Bot.on_message(filters.chat(CHANNEL_ID))
async def auto_post(client,message):

    if not (message.document or message.video):
        return

    media=message.document or message.video
    fname=media.file_name
    size=media.file_size

    title,year,season,episode,res,codec,source = parse_filename(fname)

    audio_type,languages = detect_audio(fname)

    is_series=True if season else False

    poster,rating,tmdb_year,story,genres = tmdb_fetch(title,is_series)

    show_year = year or tmdb_year or "N/A"

    # merge key
    key=f"{title.lower()}_{show_year}"
    if season:
        key+=f"_s{season}"

    # link
    code=await encode(f"get-{message.id*abs(client.db_channel.id)}")
    link=f"https://t.me/{client.username}?start={code}"

    size_mb=round(size/1024/1024,2)
    size_text=f"{size_mb} MB" if size_mb<1024 else f"{round(size_mb/1024,2)} GB"

    ep_tag=f"S{int(season):02d}E{int(episode):02d}" if season and episode else ""

    line=f"📂 ➤ {ep_tag} {res} {codec} {source} ➪ <a href='{link}'>Get File</a> ({size_text})"

    head=f"""<b>🔖 Title:</b> {title}

<b>🎬 Genres:</b> {genres}
<b>⭐️ Rating:</b> {rating}/10
<b>📆 Year:</b> {show_year}
<b>📕 Story:</b> {story}

"""

    footer=f"""

<b>🔊 Audio :</b> {audio_type} ({languages})

<b>💪 Powered By :</b> <a href="https://t.me/MzMoviiez">MzMoviiez</a>
"""

    old=await get_series(key)

    if old:
        eps=old["episodes"]
        if line not in eps:
            eps.append(line)

        # episode sort
        def sort_key(x):
            m=re.search(r"S(\d+)E(\d+)",x)
            return int(m.group(2)) if m else 9999

        eps=sorted(eps,key=sort_key)
        await update_series_episodes(key,eps)

        text=head+"\n".join(eps)+footer

        await client.edit_message_text(
            POST_CHANNEL,
            old["post_id"],
            text,
            parse_mode=ParseMode.HTML
        )
        return

    text=head+line+footer

    if poster:
        msg=await client.send_photo(
            POST_CHANNEL,
            f"https://image.tmdb.org/t/p/w500{poster}",
            caption=text,
            parse_mode=ParseMode.HTML
        )
    else:
        msg=await client.send_message(POST_CHANNEL,text,parse_mode=ParseMode.HTML)

    await save_series(key,msg.id,[line])
