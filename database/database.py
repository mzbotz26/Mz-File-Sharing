import motor.motor_asyncio
from config import DB_URI, DB_NAME

# ---------------- Mongo Client ----------------

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

# ---------------- Collections ----------------

user_data = database['users']
series_catalog = database['series_catalog']
requests_col = database['requests']

# ---------------- Default Verify ----------------

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

# ---------------- User System ----------------

def new_user(id):
    return {
        '_id': id,
        'verify_status': default_verify.copy()
    }

async def present_user(user_id: int):
    found = await user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    user = new_user(user_id)
    await user_data.insert_one(user)

async def db_verify_status(user_id):
    user = await user_data.find_one({'_id': user_id})
    if user:
        return user.get('verify_status', default_verify)
    return default_verify

async def db_update_verify_status(user_id, verify):
    await user_data.update_one(
        {'_id': user_id},
        {'$set': {'verify_status': verify}},
        upsert=True
    )

async def full_userbase():
    user_docs = user_data.find()
    return [doc['_id'] async for doc in user_docs]

async def del_user(user_id: int):
    await user_data.delete_one({'_id': user_id})

# ---------------- Series Catalog ----------------

async def get_series(title):
    return await series_catalog.find_one({"title": title})

async def save_series(title, post_id, episodes):
    await series_catalog.update_one(
        {"title": title},
        {"$set": {
            "title": title,
            "post_id": post_id,
            "episodes": episodes
        }},
        upsert=True
    )

async def update_series_episodes(title, episodes):
    await series_catalog.update_one(
        {"title": title},
        {"$set": {"episodes": episodes}}
    )

# ---------------- User Requests ----------------

async def add_request(user_id, name, request):
    await requests_col.insert_one({
        "user_id": user_id,
        "name": name,
        "request": request,
        "status": "pending"
    })

async def get_requests(limit=20):
    return requests_col.find().sort("_id", -1).limit(limit)

async def approve_request(request_text):
    data = await requests_col.find_one({"request": request_text})
    if not data:
        return None
    await requests_col.update_one(
        {"_id": data["_id"]},
        {"$set": {"status": "approved"}}
    )
    return data

async def clear_requests():
    await requests_col.delete_many({})
