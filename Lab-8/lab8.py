# Single-cell Python script for:
# 1. Generating Doc2Vec embeddings (three configurations) and clustering
# 2. Generating Word2Vec + bag-of-bins embeddings and clustering
# 3. Evaluating cluster quality via silhouette scores (using cosine distance)
# 4. Generating bar charts and PCA scatter plots for visual comparison

# -----------------------------------------------------
# 1. Imports and Basic Setup
# -----------------------------------------------------
import pandas as pd
import numpy as np
import nltk
import re
import string
import matplotlib.pyplot as plt

from nltk.tokenize import word_tokenize
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.models import Word2Vec
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

nltk.download('punkt_tab') 

# -----------------------------------------------------
# 2. Load CSV and Preprocess
# -----------------------------------------------------
df = pd.read_csv('reddit_posts.csv')
text_column = "cleaned_text"


def preprocess_text(text):
    text = text.lower()  # lowercase
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)  # remove punctuation
    tokens = word_tokenize(text)
    return tokens


df["tokens"] = df[text_column].astype(str).apply(preprocess_text)

# -----------------------------------------------------
# 3. Doc2Vec Embeddings & Clustering
# -----------------------------------------------------
# Prepare TaggedDocument objects for Doc2Vec
tagged_data = [TaggedDocument(words=row["tokens"], tags=[i]) for i, row in df.iterrows()]

doc2vec_configs = [
    {"vector_size": 50, "min_count": 2, "epochs": 20},
    {"vector_size": 100, "min_count": 2, "epochs": 20},
    {"vector_size": 200, "min_count": 2, "epochs": 20},
]

doc2vec_models = []
doc2vec_embeddings = []
doc2vec_labels = []  # to store clustering labels
doc2vec_sil_scores = []  # to store silhouette scores

for config in doc2vec_configs:
    model = Doc2Vec(vector_size=config["vector_size"],
                    min_count=config["min_count"],
                    epochs=config["epochs"],
                    dm=1,  # distributed memory
                    workers=4)
    model.build_vocab(tagged_data)
    model.train(tagged_data, total_examples=model.corpus_count, epochs=model.epochs)
    doc2vec_models.append(model)

    # Infer vector for each document
    vectors = np.array([model.infer_vector(doc.words) for doc in tagged_data])
    doc2vec_embeddings.append(vectors)

    # Cluster using KMeans (using 3 clusters as an example)
    kmeans = KMeans(n_clusters=3, random_state=42)
    labels = kmeans.fit_predict(vectors)
    doc2vec_labels.append(labels)

    # Compute silhouette score (using cosine distance)
    sil_score = silhouette_score(vectors, labels, metric='cosine')
    doc2vec_sil_scores.append(sil_score)

    print(f"Doc2Vec (vector_size={config['vector_size']}): silhouette score = {sil_score}")

# -----------------------------------------------------
# 4. Word2Vec + Bag-of-Bins Embeddings & Clustering
# -----------------------------------------------------
all_tokens = df["tokens"].tolist()
word2vec_dims = [50, 100, 200]
word2vec_models = []
word_clusters_list = []  # will hold word-to-bin mapping for each dimension
unique_words = list({w for tokens in all_tokens for w in tokens})
num_word_bins = 10  # choose number of bins for clustering words

for dim in word2vec_dims:
    w2v_model = Word2Vec(sentences=all_tokens,
                         vector_size=dim,
                         min_count=2,
                         workers=4,
                         epochs=20)
    word2vec_models.append(w2v_model)

    # Get embeddings for each unique word present in the model
    word_vectors = np.array([w2v_model.wv[w] for w in unique_words if w in w2v_model.wv])

    # Cluster word vectors into bins using KMeans
    kmeans_words = KMeans(n_clusters=num_word_bins, random_state=42)
    word_labels = kmeans_words.fit_predict(word_vectors)

    # Map each word to its bin (using order from unique_words, skipping words not in vocabulary)
    word_to_bin = {}
    idx = 0
    for w in unique_words:
        if w in w2v_model.wv:
            word_to_bin[w] = word_labels[idx]
            idx += 1
    word_clusters_list.append(word_to_bin)

# For each Word2Vec dimension, build document vectors based on word bin frequencies, cluster, and evaluate
word2vec_labels = []  # clustering labels for each dimension
word2vec_sil_scores = []  # silhouette scores for each dimension
word2vec_doc_vectors_list = []  # store document vectors for later PCA scatter plots

for dim_idx, dim in enumerate(word2vec_dims):
    word_to_bin = word_clusters_list[dim_idx]
    doc_vectors = []
    for tokens in df["tokens"]:
        # Count frequency of words falling into each bin
        bin_counts = np.zeros(num_word_bins, dtype=float)
        for w in tokens:
            if w in word_to_bin:
                bin_counts[word_to_bin[w]] += 1.0
        # Normalize by total words in the document
        total_words = len(tokens)
        if total_words > 0:
            bin_counts /= total_words
        doc_vectors.append(bin_counts)
    doc_vectors = np.array(doc_vectors)
    word2vec_doc_vectors_list.append(doc_vectors)

    kmeans_docs = KMeans(n_clusters=3, random_state=42)
    labels = kmeans_docs.fit_predict(doc_vectors)
    word2vec_labels.append(labels)

    sil_score = silhouette_score(doc_vectors, labels, metric='cosine')
    word2vec_sil_scores.append(sil_score)

    print(f"Word2Vec Bin (dimension={dim}): silhouette score = {sil_score}")

# -----------------------------------------------------
# 5. Plotting the Silhouette Scores for Comparison
# -----------------------------------------------------
dimensions = [config["vector_size"] for config in doc2vec_configs]  # should match word2vec_dims

x = np.arange(len(dimensions))
width = 0.35

fig, ax = plt.subplots(figsize=(8, 6))
rects1 = ax.bar(x - width / 2, doc2vec_sil_scores, width, label='Doc2Vec')
rects2 = ax.bar(x + width / 2, word2vec_sil_scores, width, label='Word2Vec Bin')

ax.set_ylabel('Silhouette Score (Cosine)')
ax.set_xlabel('Embedding Dimension')
ax.set_title('Embedding Methods Comparison by Silhouette Score')
ax.set_xticks(x)
ax.set_xticklabels(dimensions)
ax.legend()

for rect in rects1 + rects2:
    height = rect.get_height()
    ax.annotate(f'{height:.2f}',
                xy=(rect.get_x() + rect.get_width() / 2, height),
                xytext=(0, 3),  # 3 points vertical offset
                textcoords="offset points",
                ha='center', va='bottom')

plt.show()

# -----------------------------------------------------
# 6. PCA Scatter Plots for a Selected Dimension (e.g., 100)
# -----------------------------------------------------
selected_dim = 100
selected_idx = dimensions.index(selected_dim)
pca = PCA(n_components=2)

# Doc2Vec PCA projection
doc2vec_reduced = pca.fit_transform(doc2vec_embeddings[selected_idx])
plt.figure(figsize=(6, 5))
plt.scatter(doc2vec_reduced[:, 0], doc2vec_reduced[:, 1],
            c=doc2vec_labels[selected_idx], cmap='viridis', alpha=0.7)
plt.title(f"Doc2Vec Clusters (Dimension {selected_dim}) - PCA Projection")
plt.xlabel("Principal Component 1")
plt.ylabel("Principal Component 2")
plt.colorbar(label='Cluster Label')
plt.show()

# Word2Vec Bin PCA projection
word2vec_reduced = pca.fit_transform(word2vec_doc_vectors_list[selected_idx])
plt.figure(figsize=(6, 5))
plt.scatter(word2vec_reduced[:, 0], word2vec_reduced[:, 1],
            c=word2vec_labels[selected_idx], cmap='viridis', alpha=0.7)
plt.title(f"Word2Vec Bin Clusters (Dimension {selected_dim}) - PCA Projection")
plt.xlabel("Principal Component 1")
plt.ylabel("Principal Component 2")
plt.colorbar(label='Cluster Label')
plt.show()
