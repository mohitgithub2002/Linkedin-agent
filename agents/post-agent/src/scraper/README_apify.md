# LinkedIn Data Fetcher with Apify

This module fetches LinkedIn data using the Apify platform's LinkedIn scraper actor and automatically analyzes the content.

## Setup

1. Create a `.env` file in the root directory with your Apify API token:
   ```
   APIFY_API_TOKEN=your_api_token_here
   ```
   You can get your API token from [https://console.apify.com/account/integrations](https://console.apify.com/account/integrations)

## Usage

### FastAPI Endpoint

The main way to use this functionality is through the FastAPI endpoint:

```
POST /fetch-linkedin-data
```

Request body:
```json
{
  "username": "satyanadella",
  "page_number": 1,
  "limit": 100
}
```

Response:
```json
{
  "data": [...],
  "file_path": "data/satyanadella/data.json",
  "analysis": {
    "top_posts": [...],
    "stats": {
      "total_reactions": 5000,
      "total_comments": 300,
      "total_reposts": 150,
      "average_engagement_score": 45.7
    },
    "output_file": "data/satyanadella/top_performing_posts.json"
  },
  "status": "success"
}
```

Example using curl:
```bash
curl -X POST "http://localhost:8000/fetch-linkedin-data" \
  -H "Content-Type: application/json" \
  -d '{"username": "satyanadella", "page_number": 1, "limit": 100}'
```

### Command Line

You can also run the script directly from the command line:

```bash
python src/scraper/linkedin_post_fetcher.py --username satyanadella
```

The script will use the APIFY_API_TOKEN from your environment variables.

Optional parameters:
- `--api_token`: Override the API token from environment variable
- `--page_number`: Page number to start from (default: 1)
- `--limit`: Maximum number of posts to fetch (default: 100)

### Interactive Mode

For an interactive prompt:

```bash
python src/fetch_linkedin_data.py
```

This will ask for the username and other optional parameters, and will use the API token from your `.env` file.

### From Another Script

You can also import the function and use it in your own scripts:

```python
from src.scraper.linkedin_post_fetcher import fetch_and_save_linkedin_data

# Fetch data for a specific user
result = fetch_and_save_linkedin_data(
    username="satyanadella",
    # api_token is optional, will use environment variable if not provided
    page_number=1,
    limit=100
)

if result["data"]:
    print(f"Retrieved {len(result['data'])} items")
    print(f"Analysis saved to {result['analysis']['output_file']}")
```

## Data Storage

The system creates two files for each username:

1. Raw LinkedIn data:
```
data/{username}/data.json
```

2. Analyzed top-performing posts:
```
data/{username}/top_performing_posts.json
```

The analysis includes:
- Top-performing posts ranked by engagement score
- Engagement metrics (reactions, comments, reposts)
- Time-based analysis giving higher weight to recent popular posts 