import json
import datetime
from pathlib import Path

def load_json_data(file_path):
    """Load JSON data from file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def calculate_engagement_score(post, current_time=None):
    """
    Calculate an engagement score based on reactions, comments, reposts, and time
    Time factor gives more weight to recent posts that achieved high engagement quickly
    """
    # Get engagement metrics
    total_reactions = post.get('stats', {}).get('total_reactions', 0)
    comments = post.get('stats', {}).get('comments', 0)
    reposts = post.get('stats', {}).get('reposts', 0)
    
    # Calculate base score with higher weight to comments (2x) and reposts (3x)
    base_score = total_reactions + (comments * 2) + (reposts * 3)
    
    # Apply time factor if timestamp is available
    if current_time and 'posted_at' in post and 'timestamp' in post['posted_at']:
        post_timestamp = post['posted_at']['timestamp'] / 1000  # Convert milliseconds to seconds
        time_diff_days = (current_time - post_timestamp) / (24 * 60 * 60)  # Convert to days
        
        # Give bonus to newer posts (recency factor)
        if time_diff_days < 7:  # If less than a week old
            time_factor = 1.5
        elif time_diff_days < 14:  # If less than two weeks old
            time_factor = 1.2
        elif time_diff_days < 30:  # If less than a month old
            time_factor = 1.1
        else:
            time_factor = 1.0
            
        return base_score * time_factor
    
    return base_score

def extract_top_posts(posts, top_n=10, current_time=None):
    """Extract top performing posts based on engagement score"""
    # Calculate engagement score for each post
    for post in posts:
        post['engagement_score'] = calculate_engagement_score(post, current_time)
    
    # Sort posts by engagement score in descending order
    sorted_posts = sorted(posts, key=lambda x: x['engagement_score'], reverse=True)
    
    # Return top N posts
    return sorted_posts[:top_n]

def create_simplified_data(posts):
    """Create simplified data with only the required fields"""
    simplified_data = []
    
    for post in posts:
        simplified_post = {
            'url': post.get('url', ''),
            'text': post.get('text', ''),
            'posted_at_date': post.get('posted_at', {}).get('date', ''),
            'total_reactions': post.get('stats', {}).get('total_reactions', 0),
            'comments': post.get('stats', {}).get('comments', 0),
            'reposts': post.get('stats', {}).get('reposts', 0),
            'engagement_score': post.get('engagement_score', 0)
        }
        simplified_data.append(simplified_post)
    
    return simplified_data

def save_json_data(data, file_path):
    """Save data to a JSON file"""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def analyze_creator_posts(input_file_path, output_file_path=None, top_n=20):
    """
    Analyze LinkedIn posts and extract top performing ones.
    
    Args:
        input_file_path (str or Path): Path to the input JSON file with LinkedIn posts
        output_file_path (str or Path, optional): Path to save the analyzed data
                                                If None, will save to same folder as input
        top_n (int): Number of top posts to extract
    
    Returns:
        dict: Analysis results containing top posts and summary statistics
    """
    # Convert to Path objects
    input_file = Path(input_file_path)
    
    if output_file_path is None:
        output_file = input_file.parent / "top_performing_posts.json"
    else:
        output_file = Path(output_file_path)
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Current time (as a timestamp)
    current_time = datetime.datetime.now().timestamp()
    
    # Load data
    print(f"Loading data from {input_file}...")
    try:
        posts = load_json_data(input_file)
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return None
    
    # Extract top posts
    print("Analyzing posts based on engagement metrics...")
    top_posts = extract_top_posts(posts, top_n=top_n, current_time=current_time)
    
    # Create simplified data
    simplified_data = create_simplified_data(top_posts)
    
    # Save to file
    print(f"Saving top performing posts to {output_file}...")
    save_json_data(simplified_data, output_file)
    
    # Calculate summary statistics
    total_reactions = sum(post.get('total_reactions', 0) for post in simplified_data)
    total_comments = sum(post.get('comments', 0) for post in simplified_data)
    total_reposts = sum(post.get('reposts', 0) for post in simplified_data)
    
    # Prepare results
    results = {
        'top_posts': simplified_data,
        'stats': {
            'total_reactions': total_reactions,
            'total_comments': total_comments,
            'total_reposts': total_reposts,
            'average_engagement_score': sum(post.get('engagement_score', 0) for post in simplified_data) / len(simplified_data) if simplified_data else 0
        },
        'output_file': str(output_file)
    }
    
    print(f"Analysis complete. Top {len(top_posts)} posts saved to {output_file}")
    print(f"Top posts statistics:")
    print(f"- Total reactions: {total_reactions}")
    print(f"- Total comments: {total_comments}")
    print(f"- Total reposts: {total_reposts}")
    
    return results

def main():
    # File paths
    input_file = Path('data/nbroekema/data.json')
    output_file = Path('data/nbroekema/top_performing_posts.json')
    
    # Run analysis
    analyze_creator_posts(input_file, output_file)

if __name__ == "__main__":
    main()
