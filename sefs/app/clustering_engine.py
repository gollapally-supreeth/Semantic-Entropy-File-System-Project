import umap
import hdbscan
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score
import numpy as np
from .config import Config


class ClusteringEngine:
    def __init__(self):
        """Initialize advanced clustering with UMAP + HDBSCAN"""
        print("Initializing UMAP + HDBSCAN clustering engine...")
        
    def perform_clustering(self, embeddings):
        """
        Advanced semantic clustering using UMAP + HDBSCAN.
        This is state-of-the-art for semantic document clustering.
        """
        if not embeddings or len(embeddings) == 0:
            return []
        
        X = np.array(embeddings)
        n_samples = len(X)
        
        print(f"DEBUG: Clustering {n_samples} files with HDBSCAN + UMAP")
        
        # For very small datasets, use simple approach
        if n_samples < 3:
            return [0] * n_samples
        
        # Step 1: UMAP dimensionality reduction
        # Reduces 768-dim MPNet embeddings to 5-dim while preserving semantic structure
        n_neighbors = min(15, n_samples - 1)
        n_components = min(5, n_samples - 1)
        
        print(f"DEBUG: UMAP reduction: 768 → {n_components} dimensions")
        umap_model = umap.UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            metric='cosine',
            min_dist=0.0,
            random_state=42
        )
        
        reduced_embeddings = umap_model.fit_transform(X)
        
        # Step 2: HDBSCAN clustering
        # Automatically finds optimal number of clusters based on density
        min_cluster_size = 2 if n_samples < 10 else 3
        min_samples = 1 if n_samples < 10 else 2
        
        print(f"DEBUG: HDBSCAN clustering (min_cluster_size={min_cluster_size})")
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric='euclidean',
            cluster_selection_method='eom',  # Excess of Mass
            prediction_data=True
        )
        
        labels = clusterer.fit_predict(reduced_embeddings)
        
        # Step 3: Quality metrics
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        
        print(f"DEBUG: Found {n_clusters} clusters, {n_noise} noise points")
        
        # Calculate quality scores
        if n_clusters > 1 and n_samples > n_clusters:
            # Only calculate for non-noise points
            non_noise_mask = labels != -1
            if np.sum(non_noise_mask) > 1:
                try:
                    silhouette = silhouette_score(
                        reduced_embeddings[non_noise_mask], 
                        labels[non_noise_mask]
                    )
                    davies_bouldin = davies_bouldin_score(
                        reduced_embeddings[non_noise_mask],
                        labels[non_noise_mask]
                    )
                    print(f"DEBUG: Quality - Silhouette: {silhouette:.3f}, Davies-Bouldin: {davies_bouldin:.3f}")
                    print(f"DEBUG: (Silhouette: higher=better, Davies-Bouldin: lower=better)")
                except:
                    pass
        
        # Show cluster sizes
        unique_labels = set(labels)
        for label in sorted(unique_labels):
            count = list(labels).count(label)
            if label == -1:
                print(f"DEBUG: Noise: {count} files")
            else:
                print(f"DEBUG: Cluster {label}: {count} files")
        
        return labels

    def reduce_dimensions(self, embeddings):
        """
        Reduces embeddings to 2D for visualization using UMAP.
        UMAP preserves semantic structure better than PCA.
        """
        if not embeddings or len(embeddings) == 0:
            return []

        X = np.array(embeddings)
        n_samples = X.shape[0]
        
        if n_samples < 2:
            return [(0.0, 0.0)] * n_samples

        # Use UMAP for better visualization
        n_neighbors = min(15, n_samples - 1)
        
        try:
            umap_model = umap.UMAP(
                n_neighbors=n_neighbors,
                n_components=2,
                metric='cosine',
                min_dist=0.1,
                random_state=42
            )
            reduced = umap_model.fit_transform(X)
            return reduced.tolist()
        except:
            # Fallback to PCA if UMAP fails
            print("DEBUG: UMAP visualization failed, using PCA fallback")
            n_components = min(n_samples, 2)
            pca = PCA(n_components=n_components)
            reduced = pca.fit_transform(X)
            
            if n_components == 1:
                return [(float(x[0]), 0.0) for x in reduced]
                
            return reduced.tolist()
