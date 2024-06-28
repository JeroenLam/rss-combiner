import feedparser
from datetime import datetime

async def get_feed_by_name(db, feed_name: str):
    return await db.feeds.find_one({"name": feed_name})

async def get_feed_id_by_name(db, feed_name: str):
    feed = await db.feeds.find_one({"name": feed_name}, {"_id": 1})
    return feed["_id"] if feed else None

async def feed_name_exists(db, feed_name: str) -> bool:
    return await get_feed_id_by_name(db, feed_name) is not None

async def insert_feed(db, feed_data: dict):
    await db.feeds.insert_one(feed_data)

async def get_base_feeds(db):
    return await db.feeds.find({"url": {"$exists": True}}).to_list(1000)

async def get_latest_post_timestamp(db, feed_collection):
    latest_post = await db[feed_collection].find_one(sort=[("published", -1)])
    return latest_post["published"] if latest_post else None

async def get_existing_guids(db, feed_collection):
    existing_posts = await db[feed_collection].find({}, {"guid": 1}).to_list(1000)
    return {post["guid"] for post in existing_posts}

async def insert_new_posts(db, feed_collection, posts):
    await db[feed_collection].insert_many(posts)

def fetch_feed_posts(feed_url):
    feed = feedparser.parse(feed_url)
    return [
        {
            "title": entry.title,
            "link": entry.link,
            "published": datetime(*entry.published_parsed[:6]),
            "description": entry.description,
            "guid": entry.id
        }
        for entry in feed.entries
    ]