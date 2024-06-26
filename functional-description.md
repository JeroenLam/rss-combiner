Definition:
- Raw feeds: external RSS feeds
- Tags: Words used to filter elements from a raw feed (both in title and body)
- List: new feed that is a combination of multiple raw feeds filtered by tags

Backend:
- Database:
    - storing all the raw RSS feed data
    - storing a list of raw RSS feed URLs
    - storing user-created lists and related raw RSS feed IDs and tags
- Scraper:
    - Scraping the list of raw feeds for new posts and storing them in the database
- API:
    - Must be able to return both JSON and XML (RSS) of the combined feeds
    - Endpoint where the raw feeds can be found
    - Endpoint where new raw feeds can be added
    - Endpoint to create a new list
    - Endpoint to add new tags to a list
    - Endpoint to add new raw feeds to the list
    - Endpoint to retrieve the most recent 'n' posts for a specific list
    - Endpoint to show the raw feeds and tags of a list
    - Endpoint to remove raw feeds or tags from a list