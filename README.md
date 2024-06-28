# rss-combiner

## Running the application
Make sure you copy `ex.env` to `.env` and configure settings. Then run:

```bash
docker compose --env-file .env up --build -d
```

## Example data and usage of api
If you want the database to be filled with some example data, run:
```bash
./fill_test_db.sh
```
This will add the NOS tech news feed and the nu.nl tech newsfeed to the database. Once added we create a combined feed for `dutch_tech_news` which combines both NOS and nu.nl. The resulting rss feed can be found at `<your-ip>:8000/feeds/dutch_tech_news/rss/?limit=20`. The `json` version of the same content can be found at `<your-ip>:8000/feeds/dutch_tech_news/json/?limit=20`.


## Database management and api documentation
Once the application is running you can find the `Mongo Express` interface at port `<your-ip>:8081` and the `api` documentation at `<your-ip>:8000/docs`.