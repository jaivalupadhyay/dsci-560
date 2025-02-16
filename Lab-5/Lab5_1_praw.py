import praw
import time
import pandas as pd

# Reddit API credentials (replace with your own)
reddit = praw.Reddit(
    client_id="bkEPeZqGRTXTv6ER4gAXgA",
    client_secret="Le8OA1zW6o1ZCt3U0NnyYSUigc4cZA",
    user_agent="mypraw_bot/1.0 by u/Careful_Counter_5384"
)

def fetch_more_posts(subreddit_name, total_posts=5000, batch_size=100):

    subreddit = reddit.subreddit(subreddit_name)
    posts = []

    # Sorting methods to fetch more data
    sorting_methods = ["hot", "new", "top"]
    after_dict = {method: None for method in sorting_methods}  # Pagination tracker

    while len(posts) < total_posts and sorting_methods:
        for method in sorting_methods[:]:  # Iterate over sorting methods
            if len(posts) >= total_posts:
                break  # Stop when we reach the required number of posts

            try:
                # Fetch batch of posts using the current sorting method
                batch = getattr(subreddit, method)(limit=batch_size, params={"after": after_dict[method]})
                count = 0

                for post in batch:
                    posts.append({
                        "title": post.title,
                        "score": post.score,
                        "id": post.id,
                        "url": post.url,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc,
                        "selftext": post.selftext[:500]  # Limit text to 500 chars
                    })
                    count += 1
                    if len(posts) >= total_posts:
                        break  # Stop if we've reached the required number of posts

                # Update 'after' for pagination
                after_dict[method] = post.fullname if count > 0 else None
                if after_dict[method] is None:
                    sorting_methods.remove(method)  # Remove method if no more posts

                print(f"Fetched {len(posts)} posts so far...")

                # Avoid hitting API rate limits
                time.sleep(2)

            except Exception as e:
                print(f"Error fetching posts: {e}")
                time.sleep(5)  # Wait and retry in case of an error

    return posts


# Define the subreddit to fetch from
subreddit_name = "tech"  # Change this to any subreddit
posts_data = fetch_more_posts(subreddit_name)

# Save the fetched posts to a CSV file
df = pd.DataFrame(posts_data)
df.to_csv("PRAW.csv", index=True)

print("Finished fetching posts. Data saved to 'PRAW.csv'.")
