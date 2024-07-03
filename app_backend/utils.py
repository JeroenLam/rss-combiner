from datetime import datetime

import feedparser
import pytz
from dateutil.parser import parse as parse_date
from elasticsearch.helpers import async_bulk
from fastapi import HTTPException


async def mongo_get_feed_by_name(db, feed_name: str):
    return await db.feeds.find_one({"name": feed_name})


async def mongo_get_feed_id_by_name(db, feed_name: str):
    feed = await db.feeds.find_one({"name": feed_name}, {"_id": 1})
    return feed["_id"] if feed else None


async def mongo_feed_name_exists(db, feed_name: str) -> bool:
    return await mongo_get_feed_id_by_name(db, feed_name) is not None


async def mongo_insert_feed(db, feed_data: dict):
    await db.feeds.insert_one(feed_data)


async def mongo_get_base_feeds(db):
    return await db.feeds.find({"url": {"$exists": True}}).to_list(1000)


async def es_get_latest_post_timestamp(es, index):
    try:
        result = await es.search(index=index, size=1, sort="published:desc")
        if result["hits"]["hits"]:
            return result["hits"]["hits"][0]["_source"]["published"]
        return None
    except Exception as e:
        print(f"Error getting latest post timestamp from index {index}: {e}")
        return None


async def es_get_existing_rss_ids(es, feed_id, index="articles"):
    try:
        query = {
            "_source": ["id"],
            "query": {
                "term": {
                    "feed_id": feed_id
                }
            },
            "sort": [
                {
                    "published": {
                        "order": "desc"
                    }
                }
            ],
            "size": 100
        }
        result = await es.search(index=index, body=query)
        return {hit["_source"]["id"] for hit in result["hits"]["hits"]}
    except Exception as e:
        print(f"Error getting existing IDs from index {index}: {e}")
        return set()


async def es_ensure_index_exists(es, index):
    if not await es.indices.exists(index=index):
        await es.indices.create(index=index)


async def es_insert_new_posts(es, posts, index = "articles"):
    try:
        # Ensure the index exists before inserting
        await es_ensure_index_exists(es, index)

        # Use the async_bulk helper function and ensure arguments are passed as keywords
        actions = [
            {"_op_type": "index", "_index": index, "_source": post} for post in posts
        ]
        # Note the use of named keywords rather than positional arguments
        await async_bulk(es, actions)
    except Exception as e:
        print(f"Error inserting new posts into index {index}: {e}")


def fetch_feed_posts(feed_url: str):
    feed = feedparser.parse(feed_url)
    response = []
    for entry in feed.entries:
        entry["published"] = (
                datetime(*entry.published_parsed[:6])
                if "published_parsed" in entry
                else None
            )
        del entry["published_parsed"]
        response.append(entry)
    
    return response

    # return [
    #     {
    #         "title": getattr(entry, "title", None),
    #         "link": getattr(entry, "link", None),
    #         "published": (
    #             datetime(*entry.published_parsed[:6])
    #             if "published_parsed" in entry
    #             else None
    #         ),
    #         "description": getattr(entry, "description", None),
    #         "guid": getattr(entry, "id", None),
    #         "author": getattr(entry, "author", None),
    #     }
    #     for entry in feed.entries
    # ]


async def fetch_processed_posts(
    feed_name: str, es, db, limit: int = 20, visited_feeds=None
):
    if visited_feeds is None:
        visited_feeds = set()

    if feed_name in visited_feeds:
        raise HTTPException(status_code=400, detail="Circular dependency detected")

    visited_feeds.add(feed_name)

    feed = await mongo_get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    if "url" in feed:  # BASE_FEED
        index = f"rss_{feed['name']}"
        try:
            response = await es.search(index=index, size=limit, sort="published:desc")
            posts = [hit["_source"] for hit in response["hits"]["hits"]]
            for post in posts:
                post["feed"] = feed["name"]
                if post.get("published"):
                    # Ensure 'published' is parsed as a datetime and timezone-aware
                    post["published"] = parse_date(post["published"]).replace(
                        tzinfo=pytz.UTC
                    )
            return posts
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:  # DERIVED_FEED
        posts = []
        for derivation in feed["derivation"]:
            parent_posts = await fetch_processed_posts(
                derivation["parrent_name"], es, db, limit, visited_feeds
            )

            filters = derivation.get("filter", [])
            if filters:
                filtered_posts = [
                    post
                    for post in parent_posts
                    if any(
                        f.lower()
                        in (
                            post.get("title", "").lower()
                            + post.get("description", "").lower()
                        )
                        for f in filters
                    )
                ]
            else:
                filtered_posts = parent_posts

            posts.extend(filtered_posts)

        posts.sort(key=lambda x: x["published"], reverse=True)
        return posts[:limit]
