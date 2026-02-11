import os
import random
from .config import Config

class ClusteringEngine:
    def __init__(self):
        pass

    def perform_clustering(self, file_paths):
        """
        Returns cluster IDs based on file extensions.
        We can map extensions to integer IDs.
        """
        if not file_paths:
            return []

        # Create a deterministic mapping for current extensions
        # .txt -> 0, .pdf -> 1, etc.
        # sorted extensions to ensure stability
        exts = sorted(Config.EXTENSIONS)
        ext_map = {ext: i for i, ext in enumerate(exts)}
        
        labels = []
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            labels.append(ext_map.get(ext, -1)) # -1 for unk
            
        return labels

    def reduce_dimensions(self, file_paths):
        """
        Returns 2D coords for visualization.
        Groups files by extension in separate areas.
        """
        if not file_paths:
            return []

        exts = sorted(Config.EXTENSIONS)
        ext_map = {ext: i for i, ext in enumerate(exts)}
        num_clusters = len(exts)
        
        coords = []
        import math
        
        # Center points for clusters (arranged in a circle)
        radius = 5.0
        centers = {}
        for i, ext in enumerate(exts):
            angle = (2 * math.pi * i) / num_clusters
            cx = radius * math.cos(angle)
            cy = radius * math.sin(angle)
            centers[ext] = (cx, cy)

        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            cx, cy = centers.get(ext, (0, 0))
            
            # Add some jitter/spread
            jx = random.uniform(-1, 1)
            jy = random.uniform(-1, 1)
            
            coords.append((cx + jx, cy + jy))
            
        return coords
