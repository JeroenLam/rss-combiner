from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, root_validator, ValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum
from bson import ObjectId
import os
from utils import *

app = FastAPI()

mongo_url = os.environ["MONGO_URL"]
mongo_user = os.environ["MONGO_USER"]
mongo_pass = os.environ["MONGO_PASS"]
client = AsyncIOMotorClient(f"mongodb://{mongo_user}:{mongo_pass}@{mongo_url}:27017/")
db = client.rss_feed_db


# Enum to indicate the type of feed
class FeedType(Enum):
    BASE_FEED = 0
    DERIVED_FEED = 1


# Filter object
class Filters(BaseModel):
    filters: Optional[list[str]] = Field(None)


# Feed object
class FeedRequest(BaseModel):
    name: str 
    url: Optional[str] = Field(None)
    parent_feeds: Optional[list[str]] = Field(None)

    @root_validator(pre=True)
    def check_either_id_or_first_last(cls, values):
        url = values.get('url')
        parent_feeds = values.get('parent_feeds')
             
        if url is not None:
            cls.feed_type = FeedType.BASE_FEED
            if parent_feeds is not None :
                raise ValueError('Provide either "url" or both a list of feed names, not both.')
        else:
            cls.feed_type = FeedType.DERIVED_FEED
            cls.parent_ids = []
            if parent_feeds is None:
                raise ValueError('Provide either "url" or both a list of feed names.')
        
        
        return values
    
    def to_db(self):
        if self.feed_type == FeedType.BASE_FEED:
            return {
                "name": self.name,
                "url": self.url
            }
        else:
            return {
                "name": self.name,
                "parent_ids": self.parent_ids,
            }


@app.get("/feeds/")
async def get_feeds_list():
    feedcursor = await db.feeds.find({}, {"_id": 0, "name": 1}).to_list(1000)
    response = [feed['name'] for feed in feedcursor]
    response.sort()
    return response


@app.post("/feeds/", status_code=status.HTTP_201_CREATED)
async def create_feed(feed: FeedRequest):
    # Validate that the feed name is unique
    if await feed_name_exists(db, feed.name):
        raise HTTPException(status_code=409, detail="Feed name already exists.")
    
    # Validate feed types
    if feed.feed_type == FeedType.BASE_FEED:
        if not validate_rss_feed(feed.url):
            raise HTTPException(status_code=400, detail="Please provide a valid rss url.")
    else:
        for feed_name in feed.parent_feeds:
            parent_id = await feed_name_exists(db, feed_name)
            if not parent_id:
                raise HTTPException(status_code=400, detail=f"Parent feed does not exists: {feed_name}")
            feed.parent_ids.append(parent_id)

    # Add feed to the database
    await db.feeds.insert_one(feed.to_db())
    return f"Feed added: {feed.name}"


@app.get("/feeds/{feed_name}")
async def get_feed(feed_name: str):
    # Check if the feed exists
    feed = await get_feed_from_db(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    # Determine the type of the feed and return relevant information
    if "url" in feed:
        # This is a BASE_FEED
        response = {
            "name": feed["name"],
            "url": feed["url"]
        }
    else:
        # This is a DERIVED_FEED
        parent_feeds = [await db.feeds.find_one({"_id": parent_id}, {"_id": 0, "name": 1}) for parent_id in feed["parent_ids"]]
        parent_feeds_names = [parent["name"] for parent in parent_feeds]
        response = {
            "name": feed["name"],
            "parent_feeds": parent_feeds_names
        }
    
    return response


@app.delete("/feeds/{feed_name}")
async def delete_feed(feed_name: str):
    # Check if the feed exists
    feed_id = await feed_name_exists(db, feed_name)
    if not feed_id:
        raise HTTPException(status_code=400, detail=f"Feed does not exist: {feed_name}")

    # Ensure the feed isn't a parent feed for any other feeds
    child_feed = await db.feeds.find_one({"parent_ids": feed_id})
    if child_feed:
        raise HTTPException(status_code=400, detail=f"Feed '{feed_name}' is a parent to other feeds and cannot be deleted.")

    # Delete the feed
    await db.feeds.delete_one({"_id": feed_id})
    return f"Feed deleted: {feed_name}"


@app.get("/feeds/{feed_name}/filters/")
async def get_filters(feed_name: str):
    # Check if the feed exists
    feed = await get_feed_from_db(db, feed_name)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    # Ensure the feed is a DERIVED_FEED
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED does not have filters")
    
    # Return the filters
    return {"filters": feed.get("filters", [])}


@app.put("/feeds/{feed_name}/filters/")
async def update_filters(feed_name: str, filters: Filters):
    # Check if the feed exists
    feed_id = await feed_name_exists(db, feed_name)
    if not feed_id:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    feed = await db.feeds.find_one({"_id": feed_id})
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have filters")

    # Append only the filters which are not already in the list of filters
    current_filters = feed.get("filters", [])
    new_filters = [f for f in filters.filters if f not in current_filters] if filters.filters else []
    updated_filters = current_filters + new_filters

    # Update the filters in the database
    await db.feeds.update_one({"_id": feed_id}, {"$set": {"filters": updated_filters}})
    return {"message": f"Filters updated for feed: {feed_name}"}


@app.delete("/feeds/{feed_name}/filters/")
async def delete_filters(feed_name: str, filters: Optional[Filters] = None):
    # Check if the feed exists
    feed_id = await feed_name_exists(db, feed_name)
    if not feed_id:
        raise HTTPException(status_code=404, detail="Feed not found")

    # Ensure the feed is a DERIVED_FEED
    feed = await db.feeds.find_one({"_id": feed_id})
    if "url" in feed:
        raise HTTPException(status_code=400, detail="BASE_FEED cannot have filters")

    if filters and filters.filters:
        # Remove the specified filters from the existing list of filters
        current_filters = feed.get("filters", [])
        updated_filters = [f for f in current_filters if f not in filters.filters]
        await db.feeds.update_one({"_id": feed_id}, {"$set": {"filters": updated_filters}})
    else:
        # Delete all filters if no specific filters are provided
        await db.feeds.update_one({"_id": feed_id}, {"$unset": {"filters": ""}})

    return {"message": f"Filters deleted for feed: {feed_name}"}

@app.get("/feeds/{feed_name}/rss/")
def unimplemented_endpoint(feed_name: str):
    raise HTTPException(status_code=501,detail="This endpoint is not implemented yet.")

@app.get("/feeds/{feed_name}/json/")
def unimplemented_endpoint(feed_name: str):
    raise HTTPException(status_code=501,detail="This endpoint is not implemented yet.")