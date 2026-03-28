import numpy as np

class RecipeSearchEngine:
    def __init__(self, vectorizer, bm25_matrix, df):
        self.vectorizer = vectorizer
        self.bm25_matrix = bm25_matrix
        self.df = df

    def search(self, query, top_k=5):
        query_vec = self.vectorizer.transform([query])
        scores = self.bm25_matrix.dot(query_vec.T).toarray().flatten()
        rank = np.argsort(scores)[::-1]
        
        results = self.df.iloc[rank[:top_k]].copy()
        results['Score'] = scores[rank[:top_k]]
        return results