import feedparser
from datetime import datetime
from fastapi import HTTPException
import pytz

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
            "title": getattr(entry, 'title', None),
            "link": getattr(entry, 'link', None),
            "published": datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else None,
            "description": getattr(entry, 'description', None),
            "guid": getattr(entry, 'id', None),
            "author": getattr(entry, 'author', None)
        }
        for entry in feed.entries
    ]

async def fetch_processed_posts(feed_name: str, db, limit: int = 20, visited_feeds=None, base_feed_name=None):
    if visited_feeds is None:
        visited_feeds = set()

    if feed_name in visited_feeds:
        raise HTTPException(status_code=400, detail="Circular dependency detected")

    visited_feeds.add(feed_name)

    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed_id = await get_feed_id_by_name(db, feed_name)
    if not feed_id:
        raise HTTPException(status_code=404, detail="Feed not found")

    # If base_feed_name is not set, this is the base feed
    if base_feed_name is None:
        base_feed_name = feed_name

    if "url" in feed:  # BASE_FEED
        feed_collection = f"feed_{feed_id}"
        posts_cursor = db[feed_collection].find().sort("published", -1).limit(limit)
        posts = await posts_cursor.to_list(length=limit)
        for post in posts:
            post["_id"] = str(post["_id"])  # Ensure '_id' is string
            post["feed"] = base_feed_name
            if post.get("published") and not post["published"].tzinfo:
                post["published"] = post["published"].replace(tzinfo=pytz.UTC)  # Make datetime UTC aware

        return posts
    else:  # DERIVED_FEED
        posts = []
        for derivation in feed["derivation"]:
            parent_posts = await fetch_processed_posts(derivation["parrent_name"], db, limit, visited_feeds, base_feed_name)

            filters = derivation.get("filter", [])
            if filters:
                filtered_posts = [
                    post for post in parent_posts
                    if any(f.lower() in (post.get("title", "").lower() + post.get("description", "").lower()) for f in filters)
                ]
            else:
                filtered_posts = parent_posts

            posts.extend(filtered_posts)

        posts.sort(key=lambda x: x["published"], reverse=True)
        posts = posts[:limit]
        return posts