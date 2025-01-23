import requests
from bs4 import BeautifulSoup
import pandas as pd


url = "https://discuss.huggingface.co/t/nlp-for-summarization-and-classification/136871"

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

posts = soup.find_all('div', class_='post')
data = []

for post in posts:
    content = post.find('div', class_='cooked')  # Extract the text content
    if content:
        data.append(content.text.strip())


df = pd.DataFrame(data, columns=['Post Content'])
df.to_csv('huggingface_forum_posts.csv', index=False)
print("Data saved to csv")


