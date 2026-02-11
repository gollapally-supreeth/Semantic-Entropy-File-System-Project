from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
import numpy as np
from .config import Config

class ClusteringEngine:
    def __init__(self):
        self.dbscan = DBSCAN(eps=Config.DBSCAN_EPS, min_samples=Config.DBSCAN_MIN_SAMPLES, metric='cosine')

    def perform_clustering(self, embeddings):
        """
        Performs DBSCAN clustering on the embeddings.
        Returns cluster labels.
        """
        if not embeddings or len(embeddings) == 0:
            return []
        
        X = np.array(embeddings)
        
        # If fewer samples than min_samples, we might get all noise (-1)
        # But DBSCAN handles it (returns -1)
        labels = self.dbscan.fit_predict(X)
        return labels

    def reduce_dimensions(self, embeddings):
        """
        Reduces embeddings to 2D for visualization using PCA.
        Returns a list of (x, y) tuples.
        """
        if not embeddings or len(embeddings) == 0:
            return []

        X = np.array(embeddings)
        n_samples = X.shape[0]
        
        if n_samples < 2:
            return [(0.0, 0.0)] * n_samples

        # Attempt 2 components
        n_components = min(n_samples, 2)
        pca = PCA(n_components=n_components)
        reduced = pca.fit_transform(X)
        
        # If we only got 1 component, pad with 0
        if n_components == 1:
            return [(float(x[0]), 0.0) for x in reduced]
            
        return reduced.tolist()
