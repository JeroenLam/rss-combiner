from typing import Optional, List, Union
from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel, Field, root_validator, ValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum
import os
from feedgen.feed import FeedGenerator
from utils import *
from bson import json_util

app = FastAPI()

mongo_url = os.environ["MONGO_URL"]
mongo_user = os.environ["MONGO_USER"]
mongo_pass = os.environ["MONGO_PASS"]
client = AsyncIOMotorClient(f"mongodb://{mongo_user}:{mongo_pass}@{mongo_url}:27017/")
db = client.rss_feed_db


# Enum to indicate the type of feed
class FeedType(Enum):
    BASE_FEED = "base"
    DERIVED_FEED = "derived"

# Settings dataclass for the feeds
class FeedSettings(BaseModel):
    update_frequency: str
    use_description: bool
    scrape_content: bool
    create_summary: bool


# Derivation details for derived feeds
class DerivationDetail(BaseModel):
    parrent_name: str = Field(...)
    filter: Optional[List[str]]


# Feed model for Base Feeds
class FeedRequest(BaseModel):
    short_name: str
    name: str
    icon: str
    url: Optional[str] = None
    settings: Optional[FeedSettings] = None
    derivation: Optional[List[DerivationDetail]] = None

    @root_validator(pre=True)
    def check_feed_type(cls, values):
        url = values.get('url')
        derivation = values.get('derivation')
             
        if url is not None:
            cls.feed_type = FeedType.BASE_FEED
            if derivation is not None:
                raise ValueError('Provide either "url" or "derivation", not both.')
            
            if not values.get('settings'):
                raise ValueError('Base feed must include "settings".')
        else:
            cls.feed_type = FeedType.DERIVED_FEED
            if derivation is None:
                raise ValueError('Provide "derivation" for derived feed.')
            if values.get('settings'):
                raise ValueError('Derived feeds may not include "settings".')        
        
        return values
    
    def to_db(self):
        if self.feed_type == FeedType.BASE_FEED:
            return {
                "short_name": self.short_name,
                "name": self.name,
                "icon": self.icon,
                "url": self.url,
                "settings": self.settings.dict(),
            }
        else:
            return {
                "short_name": self.short_name,
                "name": self.name,
                "icon": self.icon,
                "derivation": [der.dict(by_alias=True) for der in self.derivation],
            }


@app.get("/feeds/")
async def get_feeds_list():
    feedcursor = await db.feeds.find({}, {"_id": 0, "name": 1}).to_list(1000)
    response = [feed['name'] for feed in feedcursor]
    response.sort()
    return response


@app.post("/feeds/", status_code=status.HTTP_201_CREATED)
async def create_feed(feed: FeedRequest):
    if await feed_name_exists(db, feed.name):
        raise HTTPException(status_code=409, detail="Feed name already exists.")
    
    if feed.feed_type == FeedType.BASE_FEED:
        print("Not implemented yet!") # TODO
        # if not validate_rss_feed(feed.url):
        #     raise HTTPException(status_code=400, detail="Please provide a valid rss url.")
    else:
        for deriv in feed.derivation:
            parent_id = await get_feed_id_by_name(db, deriv.parrent_name)
            if not parent_id:
                raise HTTPException(status_code=400, detail=f"Parent feed does not exist: {deriv.parrent_name}")
    
    await insert_feed(db, feed.to_db())
    return f"Feed added: {feed.name}"


@app.get("/feeds/{feed_name}")
async def get_feed(feed_name: str):
    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    if "url" in feed:
        response = {
            "short_name": feed.get("short_name"),
            "name": feed["name"],
            "icon": feed.get("icon"),
            "url": feed["url"],
            "settings": feed.get("settings"),
        }
    else:
        derivation_details = [{
            "from": deriv["parrent_name"],
            "filter": deriv.get("filter")
        } for deriv in feed["derivation"]]
        response = {
            "short_name": feed["short_name"],
            "name": feed["name"],
            "icon": feed["icon"],
            "derivation": derivation_details
        }
    
    return response


@app.delete("/feeds/{feed_name}")
async def delete_feed(feed_name: str):
    feed_id = await get_feed_id_by_name(db, feed_name)
    if not feed_id:
        raise HTTPException(status_code=400, detail=f"Feed does not exist: {feed_name}")
    
    child_feed = await db.feeds.find_one({"derivation.parrent_name": feed_id})
    if child_feed:
        raise HTTPException(status_code=400, detail=f"Feed '{feed_name}' is a parent to other feeds and cannot be deleted.")
    
    await db.feeds.delete_one({"_id": feed_id})

    # Delete the corresponding post collection
    feed_collection = f"feed_{feed_id}"
    await db.drop_collection(feed_collection)

    return f"Feed deleted: {feed_name}"

@app.post("/feeds/{feed_name}/filters/")
async def update_filters(feed_name: str, derivation_details: List[DerivationDetail]):
    # Check if the feed exists
    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have filters")

    # Update the derivation details with new filters
    for detail in feed["derivation"]:
        for new_detail in derivation_details:
            if detail["parrent_name"] == new_detail.parrent_name:
                detail["filter"] = new_detail.filter

    # Update the feed in the database
    await db.feeds.update_one({"_id": feed["_id"]}, {"$set": {"derivation": feed["derivation"]}})
    return {"message": f"Filters updated for feed: {feed_name}"}

@app.delete("/feeds/{feed_name}/filters/")
async def delete_filters(feed_name: str, derivation_details: Optional[List[DerivationDetail]] = None):
    # Check if the feed exists
    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have filters")

    if derivation_details:
        # Remove only the specified filters from the derivation details
        for detail in feed["derivation"]:
            for del_detail in derivation_details:
                if detail.get("parrent_name") == del_detail.parrent_name and detail.get("filter"):
                    detail["filter"] = [f for f in detail["filter"] if f not in del_detail.filter]
    else:
        # Remove all filters if no specific filters are provided
        for detail in feed["derivation"]:
            detail["filter"] = []

    # Update the feed in the database
    await db.feeds.update_one({"_id": feed["_id"]}, {"$set": {"derivation": feed["derivation"]}})
    return {"message": f"Filters deleted for feed: {feed_name}"}

@app.post("/feeds/{feed_name}/parent/")
async def add_parent(feed_name: str, derivation_details: List[DerivationDetail]):
    # Check if the feed exists
    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have derivation details")

    # Add new derivation details
    for new_detail in derivation_details:
        if not any(detail["parrent_name"] == new_detail.parrent_name for detail in feed["derivation"]):
            feed["derivation"].append(new_detail.dict())

    # Update the feed in the database
    await db.feeds.update_one({"_id": feed["_id"]}, {"$set": {"derivation": feed["derivation"]}})
    return {"message": f"Derivation details added for feed: {feed_name}"}

@app.delete("/feeds/{feed_name}/parent/")
async def remove_parent(feed_name: str, derivation_details: List[DerivationDetail]):
    # Check if the feed exists
    feed = await get_feed_by_name(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have derivation details")

    # Remove specified derivation details
    feed["derivation"] = [detail for detail in feed["derivation"] 
                          if not any(detail["parrent_name"] == del_detail.parrent_name for del_detail in derivation_details)]

    # Update the feed in the database
    await db.feeds.update_one({"_id": feed["_id"]}, {"$set": {"derivation": feed["derivation"]}})
    return {"message": f"Derivation details removed for feed: {feed_name}"}

@app.get("/feeds/{feed_name}/rss/")
async def get_feed_rss(feed_name: str, limit: int = 20):
    all_posts = await fetch_processed_posts(feed_name, db, limit)

    # Generate RSS feed using feedgen
    fg = FeedGenerator()
    fg.title(feed_name)
    fg.link(href=f"/feeds/{feed_name}/rss/")
    fg.description(f"RSS feed for {feed_name}")

    for post in all_posts:
        fe = fg.add_entry()
        fe.title(post.get("title"))
        fe.link(href=post.get("link"))
        fe.description(post.get("description"))
        fe.guid(post.get("guid"))
        fe.pubDate(post.get("published"))
        fe.source(post.get("feed"))

    rss_feed = fg.rss_str(pretty=True)
    return Response(content=rss_feed, media_type="application/rss+xml")

@app.get("/feeds/{feed_name}/json/")
async def get_feed_json(feed_name: str, limit: int = 20):
    all_posts = await fetch_processed_posts(feed_name, db, limit)
    return all_posts

@app.post("/update-feeds/")
async def scan_for_new_posts(background_tasks: BackgroundTasks):
    async def scan_task():
        base_feeds = await get_base_feeds(db)
        for feed in base_feeds:
            feed_collection = f"feed_{feed['_id']}"
            existing_guids = await get_existing_guids(db, feed_collection)
            new_posts = []
            
            posts = fetch_feed_posts(feed["url"])
            for post in posts:
                if post["guid"] not in existing_guids:
                    new_posts.append(post)
            
            if new_posts:
                await insert_new_posts(db, feed_collection, new_posts)

    background_tasks.add_task(scan_task)
    return {"message": "Scanning for new posts started in the background"}