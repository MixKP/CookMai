import numpy as np
import scipy.sparse as sp

class BM25Transformer:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b

    def fit(self, X):
        self.N_ = X.shape[0]
        df = np.bincount(X.indices, minlength=X.shape[1])
        self.idf_ = np.log((self.N_ - df + 0.5) / (df + 0.5) + 1.0)
        self.avgdl_ = X.sum(axis=1).mean()
        return self

    def transform(self, X):
        X = X.tocoo()
        dl = X.sum(axis=1).A1
        doc_lengths = dl[X.row]
        tf = X.data
        idf = self.idf_[X.col]
        numerator = tf * (self.k1 + 1)
        denominator = tf + self.k1 * (1 - self.b + self.b * (doc_lengths / self.avgdl_))
        data = (numerator / denominator) * idf
        return sp.csr_matrix((data, (X.row, X.col)), shape=X.shape)
