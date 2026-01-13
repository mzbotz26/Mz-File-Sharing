import motor.motor_asyncio
from config import DB_URI, DB_NAME

dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]

user_data = database['users']
series_catalog = database['series_catalog']
requests_col = database['requests']

# ---------------- USER ----------------

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {'_id': id, 'verify_status': default_verify.copy()}

async def present_user(user_id):
    return bool(await user_data.find_one({'_id': user_id}))

async def add_user(user_id):
    await user_data.insert_one(new_user(user_id))

# ---------------- SERIES / MOVIE MERGE ----------------

async def get_series(title):
    return await series_catalog.find_one({"_id": title})

async def save_series(title, post_id, episodes):
    await series_catalog.update_one(
        {"_id": title},
        {
            "$setOnInsert": {
                "post_id": post_id,
                "episodes": episodes
            }
        },
        upsert=True
    )

async def add_episode(title, line):
    await series_catalog.update_one(
        {"_id": title},
        {
            "$addToSet": {"episodes": line}
        },
        upsert=True
    )

async def update_post_id(title, post_id):
    await series_catalog.update_one(
        {"_id": title},
        {"$set": {"post_id": post_id}}
    )

async def reset_series_catalog():
    await series_catalog.delete_many({})

# ---------------- REQUESTS ----------------

async def add_request(user_id, name, request):
    await requests_col.insert_one({
        "user_id": user_id,
        "name": name,
        "request": request,
        "status": "pending"
    })

async def get_requests(limit=20):
    return requests_col.find().sort("_id",-1).limit(limit)

async def clear_requests():
    await requests_col.delete_many({})
