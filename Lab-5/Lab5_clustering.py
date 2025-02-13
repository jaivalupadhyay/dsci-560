import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from collections import Counter

# Load dataset
df = pd.read_csv("reddit_posts.csv")

# Ensure 'keywords' column exists
if 'keywords' not in df.columns:
    raise ValueError("Column 'keywords' not found in the dataset")

# Preprocess: Convert keywords into lists of words (assuming comma-separated)
df['keywords'] = df['keywords'].astype(str).apply(lambda x: x.split(','))

# Prepare data for Doc2Vec (each row needs to be a TaggedDocument)
documents = [TaggedDocument(words=row['keywords'], tags=[str(index)]) for index, row in df.iterrows()]

# Train Doc2Vec model
doc2vec_model = Doc2Vec(vector_size=100, window=5, min_count=1, workers=4, epochs=20)
doc2vec_model.build_vocab(documents)
doc2vec_model.train(documents, total_examples=doc2vec_model.corpus_count, epochs=doc2vec_model.epochs)

# Generate document embeddings
df['doc_embedding'] = df['keywords'].apply(lambda x: doc2vec_model.infer_vector(x).astype(np.float64))

# Convert to NumPy array for clustering
X = np.vstack(df['doc_embedding'].values)

# Finding the optimal K using Elbow Method
wcss_values = []
silhouette_scores = []
k_range = range(2, 11)  # Testing K values from 2 to 10

for k in k_range:
    kmeans = KMeans(n_clusters=k, init='k-means++', max_iter=500, random_state=42, n_init=10)
    kmeans.fit(X)
    wcss_values.append(kmeans.inertia_)  # Store WCSS
    silhouette_scores.append(silhouette_score(X, kmeans.labels_))

# Selecting the best K based on Silhouette Score
best_k = k_range[np.argmax(silhouette_scores)]
print(f"Optimal number of clusters (K): {best_k}")

# Apply KMeans with optimal K

kmeans = KMeans(n_clusters=best_k, init='k-means++', max_iter=500, random_state=42, n_init=10)
df['cluster'] = kmeans.fit_predict(X)

df.to_csv("intermediate.csv", index=False)

# Print final WCSS and Silhouette Score
final_wcss = kmeans.inertia_
final_silhouette_score = silhouette_score(X, kmeans.labels_)

print(f"Final WCSS (Inertia): {final_wcss}")
print(f"Final Silhouette Score: {final_silhouette_score}")

# Identify keywords for each cluster
cluster_keywords = {}
for cluster in range(best_k):
    words = [word for keywords in df[df['cluster'] == cluster]['keywords'] for word in keywords]
    cluster_keywords[cluster] = Counter(words).most_common(10)  # Top 10 keywords per cluster

print("Top Keywords per Cluster:")
for cluster, keywords in cluster_keywords.items():
    print(f"Cluster {cluster}: {[word for word, count in keywords]}")

# Reduce dimensions using PCA for visualization
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

# Store PCA-transformed coordinates for visualization
df['pca_x'] = X_pca[:, 0]
df['pca_y'] = X_pca[:, 1]

# Plot Clusters
plt.figure(figsize=(10, 6))
sns.scatterplot(x=df['pca_x'], y=df['pca_y'], hue=df['cluster'], palette='viridis', s=100, alpha=0.8)
plt.title("PCA Visualization of Keyword Clusters")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.legend(title="Cluster")
plt.show()

# Define the new keywords
new_keywords = ["AI", "deep learning", "neural networks"]

# Convert new keywords into a vector using Doc2Vec
new_vector = doc2vec_model.infer_vector(new_keywords).astype(np.float64)

# Predict cluster for the new data point
predicted_cluster = kmeans.predict([new_vector])[0]

# Reduce dimensions using PCA for visualization
new_pca = pca.transform([new_vector])[0]  # Get PCA projection of the new point

# Plot existing clusters with the new point
plt.figure(figsize=(10, 6))
sns.scatterplot(x=df['pca_x'], y=df['pca_y'], hue=df['cluster'], palette='viridis', s=100, alpha=0.8)

# Plot the new point
plt.scatter(new_pca[0], new_pca[1], color='red', s=200, edgecolors='black', label='New Keywords', marker='X')

# Annotate the new point
plt.text(new_pca[0], new_pca[1], " New Point", fontsize=12, verticalalignment='bottom', color='red')

plt.title("PCA Visualization of Keyword Clusters with New Keywords")
plt.xlabel("PCA Component 1")
plt.ylabel("PCA Component 2")
plt.legend(title="Cluster")
plt.show()

# Print the assigned cluster for the new keywords
print(f"New keywords belong to Cluster: {predicted_cluster}")

unique_clusters = sorted(df['cluster'].unique())  # Get sorted unique cluster values

plt.figure(figsize=(8, 5))
plt.hist(df['cluster'], bins=len(unique_clusters), edgecolor='black', alpha=0.7, align='mid')
plt.xticks(unique_clusters)  # Set x-axis ticks to distinct cluster values
plt.xlabel('Cluster')
plt.ylabel('Frequency')
plt.title('Histogram of Cluster Column')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()