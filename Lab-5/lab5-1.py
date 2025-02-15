import praw
import mysql.connector
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
from io import BytesIO
import pytesseract
import nltk
from nltk.corpus import stopwords
import csv  # Added for CSV export

# Ensure NLTK stopwords are downloaded (only needed once)
nltk.download('stopwords')

# --- MySQL Configuration ---

MYSQL_HOST = 'localhost'
MYSQL_USER = 'your_username'
MYSQL_PASSWORD = 'your_password'
MYSQL_DATABASE = 'reddit_scraper'  # Make sure this database exists in MySQL


def init_db():
    """
    Initialize MySQL database connection and create posts table if it doesn't exist.
    """
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = conn.cursor()
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS posts (
        post_id VARCHAR(255) PRIMARY KEY,
        title TEXT,
        author VARCHAR(255),
        created_utc DATETIME,
        cleaned_text TEXT,
        keywords TEXT,
        image_text TEXT
    )
    '''
    cursor.execute(create_table_query)
    conn.commit()
    return conn


# --- Utility Functions ---

def mask_username(username):
    """
    Masks a username to protect privacy.
    Here, we simply replace the username with a fixed pattern.
    More complex schemes could hash the username.
    """
    if username is None:
        return "Anonymous"
    return username[0] + "*" * (len(username) - 1)


def clean_text(raw_html):
    """
    Removes HTML tags and special characters from text.
    """
    soup = BeautifulSoup(raw_html, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?\']', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_keywords(text, language='english'):
    """
    A simple keyword extraction using stopword filtering.
    """
    stops = set(stopwords.words(language))  # Ensure stopwords are correctly loaded
    words = [word.strip() for word in re.findall(r'\w+', text.lower())]  # Ensure stripping of extra spaces
    keywords = [word for word in words if word not in stops and len(word) > 3]

    seen = set()
    filtered_keywords = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            filtered_keywords.append(word)

    return ','.join(filtered_keywords)


def ocr_from_image_url(image_url):
    """
    Downloads an image from a URL and performs OCR to extract text.
    Returns the OCR text or an empty string if OCR fails.
    """
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            text = pytesseract.image_to_string(image)
            return text.strip()
    except Exception as e:
        print(f"OCR error for image {image_url}: {e}")
    return ""


# --- Reddit Scraping Functions ---

def fetch_posts_praw(reddit, subreddit_name, num_posts):
    """
    Fetches posts from a subreddit using PRAW.
    Note: Reddit’s API (and thus PRAW) may return only up to ~1000 posts per listing.
    For very large requests, you may need to paginate or use Pushshift.
    """
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    fetched = 0
    for submission in subreddit.new(limit=None):
        if hasattr(submission, 'promoted') and submission.promoted:
            continue
        posts.append(submission)
        fetched += 1
        if fetched % 100 == 0:
            time.sleep(2)
        if fetched >= num_posts:
            break
    return posts


def fetch_posts_segmented(reddit, subreddit_name, num_posts):
    """
    Uses PRAW to fetch posts in segmented batches using time-based pagination.
    We repeatedly query the subreddit.new() endpoint with the 'before' parameter.
    """
    posts = []
    subreddit = reddit.subreddit(subreddit_name)
    last_timestamp = None  # No lower bound for the first batch.

    while len(posts) < num_posts:
        params = {}
        if last_timestamp is not None:
            params["before"] = last_timestamp
        print(f"Fetching batch with parameters: {params}")
        # Fetch a batch of up to 1000 posts.
        batch = list(subreddit.new(limit=1000, params=params))
        if not batch:
            print("No more posts returned. Ending segmented fetch.")
            break
        posts.extend(batch)
        # Update last_timestamp: subtract one second to avoid duplicating the last post.
        last_timestamp = batch[-1].created_utc - 1
        print(f"Total posts fetched so far: {len(posts)}")
        # If fewer than 1000 posts were returned, likely we've reached the end.
        if len(batch) < 1000:
            print("Fewer posts returned in the last batch; reached the end.")
            break

        # Sleep briefly to respect API rate limits.
        time.sleep(2)

    return posts[:num_posts]


# --- Main Processing Function ---

def process_and_store_posts(posts, conn):
    """
    Processes each post (cleans text, extracts keywords, performs OCR on images)
    and stores the result in the MySQL database.
    """
    cursor = conn.cursor()
    for post in posts:
        # Using PRAW submission objects.
        post_id = post.id
        title = post.title
        author = post.author.name if post.author else "Anonymous"
        created_utc = datetime.utcfromtimestamp(post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
        raw_text = post.selftext
        combined_text = title + "\n" + raw_text
        image_url = post.url

        cleaned = clean_text(combined_text)
        keywords = extract_keywords(cleaned)
        masked_author = mask_username(author)

        image_text = ""
        if image_url.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_text = ocr_from_image_url(image_url)

        try:
            cursor.execute('''
                INSERT IGNORE INTO posts 
                (post_id, title, author, created_utc, cleaned_text, keywords, image_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (post_id, title, masked_author, created_utc, cleaned, keywords, image_text))
            conn.commit()
        except Exception as e:
            print(f"Database insertion error for post {post_id}: {e}")


def export_to_csv(csv_filename='reddit_posts.csv'):
    """
    Exports all data from the 'posts' table in MySQL to a CSV file.
    """
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    cursor = conn.cursor()
    query = """
        SELECT post_id, title, author, created_utc, cleaned_text, keywords, image_text
        FROM posts
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(['post_id', 'title', 'author', 'created_utc', 'cleaned_text', 'keywords', 'image_text'])
        csv_writer.writerows(rows)
    print(f"Exported {len(rows)} rows to {csv_filename}")
    cursor.close()
    conn.close()


def main():
    subreddit_name = input("Enter subreddit name (e.g., tech or cybersecurity): ").strip()
    try:
        num_posts = int(input("Enter the number of posts to fetch: ").strip())
    except ValueError:
        print("Invalid number. Exiting.")
        return

    conn = init_db()

    # Initialize the Reddit instance for PRAW.
    reddit = praw.Reddit(client_id='YOUR_CLIENT_ID',
                         client_secret='YOUR_CLIENT_SECRET',
                         user_agent='reddit-scraper-example by /u/YourRedditUsername')

    # Use segmented pagination for large requests.
    if num_posts <= 1000:
        print(f"Fetching {num_posts} posts from r/{subreddit_name} using PRAW (simple listing)...")
        posts = fetch_posts_praw(reddit, subreddit_name, num_posts)
    else:
        print(f"Fetching {num_posts} posts from r/{subreddit_name} using segmented time-based pagination...")
        posts = fetch_posts_segmented(reddit, subreddit_name, num_posts)

    process_and_store_posts(posts, conn)
    print("Data fetching and processing complete.")
    conn.close()

    # Export the data from MySQL to CSV.
    print("Exporting data from MySQL to CSV...")
    export_to_csv()
    print("Export complete.")


if __name__ == "__main__":
    main()
