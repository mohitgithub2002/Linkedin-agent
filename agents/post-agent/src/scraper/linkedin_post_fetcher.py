import os
import json
from apify_client import ApifyClient
import argparse
from pathlib import Path
from dotenv import load_dotenv
from .creator_analysis import analyze_creator_posts

# Load environment variables
load_dotenv()

def fetch_and_save_linkedin_data(username, api_token=None, page_number=1, limit=100):
    """
    Fetch LinkedIn data from Apify actor and save it to the data folder
    and automatically analyze the data.
    
    Args:
        username (str): LinkedIn username to scrape
        api_token (str, optional): Your Apify API token. If None, gets from environment
        page_number (int): Page number to start from
        limit (int): Maximum number of posts to fetch
    
    Returns:
        dict: Result containing fetched data and analysis
    """
    # Get API token from environment if not provided
    if not api_token:
        api_token = os.getenv('APIFY_API_TOKEN')
        if not api_token:
            raise ValueError("APIFY_API_TOKEN not found in environment variables")
    
    # Initialize the ApifyClient with your API token
    client = ApifyClient(api_token)

    # Prepare the Actor input
    run_input = {
        "username": username,
        "page_number": page_number,
        "limit": limit,
    }

    print(f"Fetching LinkedIn data for user: {username}")
    
    try:
        # Run the Actor and wait for it to finish
        run = client.actor("LQQIXN9Othf8f7R5n").call(run_input=run_input)
        
        # Create folder structure
        folder_path = Path(f"data/{username}")
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Fetch all items from the dataset
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not items:
            print(f"No data found for user: {username}")
            return {"data": None, "analysis": None, "file_path": None}
            
        # Save data to file
        output_file = folder_path / "data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        
        print(f"Data saved to {output_file}")
        
        # Always analyze the data
        print(f"Analyzing posts for user: {username}")
        analysis_output_file = folder_path / "top_performing_posts.json"
        analysis = analyze_creator_posts(
            input_file_path=output_file,
            output_file_path=analysis_output_file
        )
        
        result = {
            "data": items,
            "file_path": str(output_file),
            "analysis": analysis
        }
            
        return result
        
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return {"data": None, "analysis": None, "file_path": None, "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch LinkedIn data from Apify')
    parser.add_argument('--username', type=str, required=True, help='LinkedIn username to scrape')
    parser.add_argument('--api_token', type=str, help='Your Apify API token (optional, can use environment variable)')
    parser.add_argument('--page_number', type=int, default=1, help='Page number to start from')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of posts to fetch')
    
    args = parser.parse_args()
    
    result = fetch_and_save_linkedin_data(
        username=args.username,
        api_token=args.api_token,
        page_number=args.page_number,
        limit=args.limit
    )
    
    if result["data"]:
        print(f"Successfully fetched {len(result['data'])} items for {args.username}")
        if result["analysis"]:
            print(f"Analysis complete. Check {result['analysis']['output_file']} for details") 