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
    stops = set(stopwords.words(language))
    words = re.findall(r'\w+', text.lower())
    keywords = [word for word in words if word not in stops and len(word) > 3]
    seen = set()
    filtered_keywords = []
    for word in keywords:
        if word not in seen:
            seen.add(word)
            filtered_keywords.append(word)
    return ', '.join(filtered_keywords)

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

def fetch_posts_pushshift(subreddit, num_posts):
    """
    Uses the Pushshift API to fetch posts from a subreddit.
    Pushshift returns a maximum of 100 posts per call, so we loop using the 'before'
    parameter to paginate through results. This function includes a retry mechanism
    to overcome individual request timeouts and is designed to handle large requests.
    """
    posts = []
    base_url = "https://api.pushshift.io/reddit/search/submission/"
    params = {
        "subreddit": subreddit,
        "size": 100,               # Maximum posts per request is typically 100.
        "sort": "desc",
        "sort_type": "created_utc"
    }
    last_created = None
    start_time = time.time()

    while len(posts) < num_posts:
        if last_created:
            params["before"] = last_created
        success = False
        attempts = 0
        # Retry mechanism: try up to 3 times per request.
        while not success and attempts < 3:
            try:
                response = requests.get(base_url, params=params, timeout=60)
                data = response.json().get("data", [])
                success = True
            except requests.exceptions.Timeout:
                attempts += 1
                print(f"Request timed out. Retrying... (Attempt {attempts} of 3)")
                time.sleep(5)
            except Exception as e:
                attempts += 1
                print(f"Pushshift error: {e}. Retrying... (Attempt {attempts} of 3)")
                time.sleep(5)
        if not success:
            print("Failed to retrieve data after 3 attempts. Breaking out of loop.")
            break
        if not data:
            print("No more data returned from Pushshift API.")
            break

        posts.extend(data)
        # Subtract 1 from the last post's created_utc to avoid duplication in the next call.
        last_created = data[-1]["created_utc"] - 1
        elapsed = time.time() - start_time
        print(f"Fetched {len(posts)} posts so far. Elapsed time: {elapsed:.2f} secs.")
        time.sleep(1)

    return posts[:num_posts]




# --- Main Processing Function ---

def process_and_store_posts(posts, conn, using_pushshift=False):
    """
    Preprocess each post and store it in the MySQL database.
    If using_pushshift is True, the post data is in Pushshift's dict format.
    Otherwise, posts are PRAW Submission objects.
    """
    cursor = conn.cursor()
    for post in posts:
        if using_pushshift:
            post_id = post.get("id")
            title = post.get("title", "")
            author = post.get("author")
            created_utc = datetime.utcfromtimestamp(post.get("created_utc")).strftime('%Y-%m-%d %H:%M:%S')
            raw_text = post.get("selftext", "")
            combined_text = title + "\n" + raw_text
            image_url = post.get("url", "")
        else:
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

# --- Main Script Execution ---

def main():
    subreddit_name = input("Enter subreddit name (e.g., tech or cybersecurity): ").strip()
    try:
        num_posts = int(input("Enter the number of posts to fetch: ").strip())
    except ValueError:
        print("Invalid number. Exiting.")
        return

    conn = init_db()

    reddit = praw.Reddit(client_id='uBNgnwJ71L3PQfAJzkjeow',
                         client_secret='J_QnMzskGLu7g5nHi2Nl6qD1HUwtCw',
                         user_agent='reddit-scraper Group-6')

    if num_posts <= 1000:
        print(f"Fetching {num_posts} posts from r/{subreddit_name} using PRAW...")
        posts = fetch_posts_praw(reddit, subreddit_name, num_posts)
        process_and_store_posts(posts, conn, using_pushshift=False)
    else:
        print(f"Fetching {num_posts} posts from r/{subreddit_name} using Pushshift API for large requests...")
        posts = fetch_posts_pushshift(subreddit_name, num_posts)
        process_and_store_posts(posts, conn, using_pushshift=True)

    print("Data fetching and processing complete.")
    conn.close()

if __name__ == "__main__":
    main()
