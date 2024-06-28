# Add NOS tech feed to the db
curl -X 'POST' \
  'http://localhost:8000/feeds/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "short_name": "nos_tech",
  "name": "nos_tech",
  "icon": "string",
  "url": "https://feeds.nos.nl/nosnieuwstech",
  "settings": {
    "update_frequency": "60m",
    "use_description": true,
    "scrape_content": true,
    "create_summary": true
  }
}'

# Add Nu.nl tech feed to the db
curl -X 'POST' \
  'http://localhost:8000/feeds/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "short_name": "nu_tech",
  "name": "nu_tech",
  "icon": "string",
  "url": "https://www.nu.nl/rss/Tech",
  "settings": {
    "update_frequency": "60m",
    "use_description": true,
    "scrape_content": true,
    "create_summary": true
  }
}'

# Create a combination feed for dutch tech news
curl -X 'POST' \
  'http://localhost:8000/feeds/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "short_name": "tech_nl",
  "name": "dutch_tech_news",
  "icon": "string",
  "derivation": [
    {
      "parrent_name": "nos_tech",
      "filter": []
    },
    {
      "parrent_name": "nu_tech",
      "filter": []
    }
  ]
}'

# Update the content in the database based on the feeds present in the database
curl -X 'POST' \
  'http://localhost:8000/update-feeds/' \
  -H 'accept: application/json' \
  -d ''