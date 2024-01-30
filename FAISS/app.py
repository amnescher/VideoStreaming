import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss

# Example text data
texts = ["Zerbra technology", "FAISS is fun", "Hello FAISS", "Machine learning is great"]

# Vectorize text data
vectorizer = TfidfVectorizer()
tfidf_vectors = vectorizer.fit_transform(texts).toarray()

# Dimension of vectors
d = tfidf_vectors.shape[1]

# Index file path
index_file = 'faiss_index.idx'

# Create a FAISS index or load if exists
if os.path.exists(index_file):
    # Load the index file if it exists
    index = faiss.read_index(index_file)
else:
    # Create a new index
    index = faiss.IndexFlatL2(d)  # L2 distance for similarity
    index.add(tfidf_vectors.astype(np.float32))
    # Save the index to disk
    faiss.write_index(index, index_file)

# Example query
query_vector = vectorizer.transform(["Hello FAISS"]).toarray()

# Perform a search for the top k similar items
k = 2  # Number of nearest neighbors
distances, indices = index.search(query_vector.astype(np.float32), k)

print("Indices of Nearest Neighbors:", indices)
print("Distances:", distances)
