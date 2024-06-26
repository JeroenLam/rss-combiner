from bson.objectid import ObjectId


def todo(crash: bool = False):
    if crash:
        raise("Warning: not implemented!")
    print("Warning: not implemented!")


def validate_rss_feed(url: str) -> bool:
    return True

async def feed_name_exists(db, name: str) -> str:
    feed = await db.feeds.find_one({"name": name}, {"_id": 1})
    if feed:
        return feed['_id']
    else:
        return None

async def get_feed_from_db(db, name: str):
    return await db.feeds.find_one({"name": name})