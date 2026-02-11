from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsSimpleTextItem
from PyQt6.QtGui import QBrush, QPen, QColor, QPainter
from PyQt6.QtCore import Qt, pyqtSignal
import random

class GraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.file_nodes = {}  # filepath: item
        
        # Colors for clusters
        self.colors = [
            QColor("#e74c3c"), QColor("#3498db"), QColor("#2ecc71"), 
            QColor("#f1c40f"), QColor("#9b59b6"), QColor("#e67e22")
        ]

    def update_graph(self, files_data, reduced_coords):
        """
        updates the graph with new positions.
        files_data: list of dicts/tuples correctly ordered with reduced_coords
        reduced_coords: list of (x, y) tuples
        """
        self.scene.clear()
        self.file_nodes.clear()

        if not files_data or not reduced_coords:
            return

        # Normalize coords to fit in view roughly
        # This is a naive normalization, standardizing to a 600x600 box
        xs = [c[0] for c in reduced_coords]
        ys = [c[1] for c in reduced_coords]
        
        if not xs or not ys:
            return

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        range_x = max_x - min_x if max_x != min_x else 1
        range_y = max_y - min_y if max_y != min_y else 1
        
        scale = 500
        
        for i, file_info in enumerate(files_data):
            # file_info = (file_path, cluster_id, ...)
            # Assuming file_info is the row from the DB or similar object
            # Let's assume it's a dict or similar for now, we'll align in integration
            
            x = (reduced_coords[i][0] - min_x) / range_x * scale - (scale/2)
            y = (reduced_coords[i][1] - min_y) / range_y * scale - (scale/2)
            
            cluster_id = file_info[4] # Index 4 is cluster_id in the DB schema
            file_path = file_info[1]
            
            color = self.colors[cluster_id % len(self.colors)] if cluster_id != -1 else QColor("#95a5a6")
            
            node = QGraphicsEllipseItem(-10, -10, 20, 20)
            node.setBrush(QBrush(color))
            node.setPen(QPen(Qt.GlobalColor.black))
            node.setToolTip(f"{file_path}\nCluster: {cluster_id}")
            node.setPos(x, y)
            
            self.scene.addItem(node)
            self.file_nodes[file_path] = node
