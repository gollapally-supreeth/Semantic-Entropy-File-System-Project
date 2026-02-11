from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QGraphicsLineItem, QGraphicsPathItem)
from PyQt6.QtGui import QBrush, QPen, QColor, QPainter, QFont, QPainterPath, QRadialGradient
from PyQt6.QtCore import Qt, QLineF, QPointF
import os
import subprocess
import platform
from collections import defaultdict
import math


class FileNode(QGraphicsEllipseItem):
    """Interactive node with modern gradient styling"""
    
    def __init__(self, file_data, color, node_type='file', parent=None):
        size = 50 if node_type == 'root' else 35 if node_type == 'cluster' else 20
        super().__init__(-size/2, -size/2, size, size, parent)
        
        self.file_data = file_data
        self.node_type = node_type
        self.base_color = color
        
        # Create gradient brush
        gradient = QRadialGradient(0, 0, size/2)
        gradient.setColorAt(0, color.lighter(140))
        gradient.setColorAt(0.7, color)
        gradient.setColorAt(1, color.darker(120))
        
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(QColor("#ffffff"), 3))
        self.setZValue(2)  # Nodes above edges
        
        # Enable interactions only for files
        if node_type == 'file':
            self.setAcceptHoverEvents(True)
            self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def hoverEnterEvent(self, event):
        """Highlight and show tooltip"""
        if self.node_type == 'file':
            self.setPen(QPen(QColor("#FFD700"), 4))  # Gold highlight
            self.setScale(1.2)
            tooltip = self._create_tooltip()
            self.setToolTip(tooltip)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """Restore appearance"""
        if self.node_type == 'file':
            self.setPen(QPen(QColor("#ffffff"), 3))
            self.setScale(1.0)
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        """Open file on click"""
        if event.button() == Qt.MouseButton.LeftButton and self.node_type == 'file':
            file_path = self.file_data['path']
            self._open_file(file_path)
        super().mousePressEvent(event)
        
    def _create_tooltip(self):
        """Generate rich tooltip"""
        data = self.file_data
        filename = os.path.basename(data['path'])
        file_ext = os.path.splitext(filename)[1].upper()
        
        try:
            size_bytes = os.path.getsize(data['path'])
            size_str = self._format_size(size_bytes)
        except:
            size_str = "Unknown"
        
        cluster = data.get('cluster_name', f"Cluster {data.get('cluster_id', -1)}")
        preview = data.get('content_sample', '')[:100]
        if len(preview) == 100:
            preview += "..."
            
        tooltip = f"""<div style='padding: 8px; background: #2c3e50; color: white;'>
            <b style='font-size: 13pt; color: #3498db;'>📄 {filename}</b><br/>
            <hr style='margin: 5px 0; border-color: #34495e;'/>
            <b>Type:</b> <span style='color: #1abc9c;'>{file_ext}</span><br/>
            <b>Size:</b> <span style='color: #f39c12;'>{size_str}</span><br/>
            <b>Cluster:</b> <span style='color: #e74c3c;'>{cluster}</span><br/>
            <b>Preview:</b><br/>
            <i style='color: #95a5a6;'>{preview}</i>
            <hr style='margin: 5px 0; border-color: #34495e;'/>
            <small style='color: #FFD700;'>✨ Click to open</small>
        </div>"""
        return tooltip
        
    def _format_size(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"
        
    def _open_file(self, file_path):
        """Open file in default application"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
        except Exception as e:
            print(f"Error opening file: {e}")


class GraphView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # Modern color palette
        self.cluster_colors = [
            QColor("#e74c3c"), QColor("#3498db"), QColor("#2ecc71"),
            QColor("#f39c12"), QColor("#9b59b6"), QColor("#1abc9c"),
            QColor("#e67e22"), QColor("#34495e"), QColor("#16a085"),
            QColor("#d35400"), QColor("#c0392b"), QColor("#8e44ad")
        ]
        
        # Dark modern background
        self.setBackgroundBrush(QBrush(QColor("#1a1a2e")))

    def update_graph(self, files_data, reduced_coords=None):
        """Build radial graph with hierarchical edges"""
        self.scene.clear()
        if not files_data:
            return

        # Group files by type and cluster
        type_clusters = defaultdict(lambda: defaultdict(list))
        for file_info in files_data:
            ext = os.path.splitext(file_info['path'])[1].lower()
            cluster_id = file_info.get('cluster_id', -1)
            type_clusters[ext][cluster_id].append(file_info)
        
        # Calculate positions using radial layout
        nodes_data = []
        edges = []
        
        # Root at center
        root_pos = (0, 0)
        root_node = FileNode({'path': 'Root'}, QColor("#16213e"), 'root')
        root_node.setPos(*root_pos)
        self.scene.addItem(root_node)
        
        # Add root label
        root_label = QGraphicsTextItem("All Files")
        root_label.setDefaultTextColor(QColor("#ffffff"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        root_label.setFont(font)
        root_label.setPos(-30, 35)
        self.scene.addItem(root_label)
        
        # Type level - inner ring
        type_radius = 200
        type_nodes = {}
        type_list = sorted(type_clusters.keys())
        type_angle_step = 2 * math.pi / max(len(type_list), 1)
        
        for i, ext in enumerate(type_list):
            angle = i * type_angle_step
            x = type_radius * math.cos(angle)
            y = type_radius * math.sin(angle)
            
            color = self.cluster_colors[i % len(self.cluster_colors)]
            node = FileNode({'path': ext}, color, 'cluster')
            node.setPos(x, y)
            self.scene.addItem(node)
            type_nodes[ext] = (node, (x, y))
            
            # Edge from root to type
            self._add_edge(root_pos, (x, y), color.lighter(150), 2)
            
            # Type label
            label = QGraphicsTextItem(ext.upper())
            label.setDefaultTextColor(color.lighter(160))
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            label.setFont(font)
            label.setPos(x - 15, y + 25)
            self.scene.addItem(label)
        
        # Cluster and file levels - outer rings
        cluster_radius = 350
        file_radius = 500
        
        for ext, clusters in type_clusters.items():
            type_node, type_pos = type_nodes[ext]
            
            # Calculate angle range for this type
            type_idx = type_list.index(ext)
            angle_start = type_idx * type_angle_step - type_angle_step/2
            angle_end = type_idx * type_angle_step + type_angle_step/2
            
            cluster_list = sorted(clusters.keys())
            cluster_angle_step = (angle_end - angle_start) / max(len(cluster_list), 1)
            
            for j, cluster_id in enumerate(cluster_list):
                cluster_angle = angle_start + (j + 0.5) * cluster_angle_step
                cluster_x = cluster_radius * math.cos(cluster_angle)
                cluster_y = cluster_radius * math.sin(cluster_angle)
                
                color = self.cluster_colors[cluster_id % len(self.cluster_colors)]
                cluster_node = FileNode({'path': f'C{cluster_id}'}, color, 'cluster')
                cluster_node.setPos(cluster_x, cluster_y)
                self.scene.addItem(cluster_node)
                
                # Edge from type to cluster
                self._add_edge(type_pos, (cluster_x, cluster_y), color.lighter(130), 1.5)
                
                # File level
                files = clusters[cluster_id]
                file_count = len(files)
                file_angle_step = cluster_angle_step / max(file_count, 1)
                
                for k, file_info in enumerate(files[:20]):  # Limit for visual clarity
                    file_angle = angle_start + j * cluster_angle_step + k * file_angle_step
                    file_x = file_radius * math.cos(file_angle)
                    file_y = file_radius * math.sin(file_angle)
                    
                    file_node = FileNode(file_info, color, 'file')
                    file_node.setPos(file_x, file_y)
                    self.scene.addItem(file_node)
                    
                    # Edge from cluster to file
                    self._add_edge((cluster_x, cluster_y), (file_x, file_y), color.darker(110), 1)
        
        # Fit view
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def _add_edge(self, start, end, color, width):
        """Add curved edge between nodes"""
        path = QPainterPath()
        path.moveTo(QPointF(*start))
        
        # Calculate control point for curve
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
        # Offset control point perpendicular to line
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)
        if length > 0:
            offset = length * 0.1
            ctrl_x = mid_x - dy/length * offset
            ctrl_y = mid_y + dx/length * offset
        else:
            ctrl_x, ctrl_y = mid_x, mid_y
        
        path.quadTo(QPointF(ctrl_x, ctrl_y), QPointF(*end))
        
        edge = QGraphicsPathItem(path)
        edge.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        edge.setZValue(0)  # Edges below nodes
        edge.setOpacity(0.6)
        self.scene.addItem(edge)

    def wheelEvent(self, event):
        """Zoom with mouse wheel"""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1/zoom_factor, 1/zoom_factor)
