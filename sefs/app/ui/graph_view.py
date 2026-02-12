from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, 
                             QGraphicsTextItem, QGraphicsPathItem)
from PyQt6.QtGui import QBrush, QPen, QColor, QPainter, QFont, QPainterPath, QRadialGradient
from PyQt6.QtCore import Qt, QPointF
import os
import subprocess
import platform
from collections import defaultdict
import math


class FileNode(QGraphicsEllipseItem):
    """Interactive node with modern gradient styling"""
    
    def __init__(self, file_data, color, node_type='file', parent=None):
        size = 50 if node_type == 'root' else 35 if node_type == 'cluster' else 25 if node_type == 'type' else 18
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
        self.setZValue(2)
        
        # Enable interactions only for files
        if node_type == 'file':
            self.setAcceptHoverEvents(True)
            self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def hoverEnterEvent(self, event):
        if self.node_type == 'file':
            self.setPen(QPen(QColor("#FFD700"), 4))
            self.setScale(1.2)
            tooltip = self._create_tooltip()
            self.setToolTip(tooltip)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        if self.node_type == 'file':
            self.setPen(QPen(QColor("#ffffff"), 3))
            self.setScale(1.0)
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.node_type == 'file':
            file_path = self.file_data['path']
            self._open_file(file_path)
        super().mousePressEvent(event)
        
    def _create_tooltip(self):
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
        
        self.type_colors = {
            '.pdf': QColor("#e74c3c"),
            '.docx': QColor("#3498db"),
            '.txt': QColor("#2ecc71"),
            '.doc': QColor("#3498db"),
        }
        
        self.setBackgroundBrush(QBrush(QColor("#1a1a2e")))

    def update_graph(self, files_data, reduced_coords=None):
        """Build radial graph: Root → Clusters → Types → Files"""
        self.scene.clear()
        if not files_data:
            return

        # Group by CLUSTER FIRST, then type
        cluster_groups = defaultdict(lambda: defaultdict(list))
        for file_info in files_data:
            cluster_id = file_info.get('cluster_id', -1)
            ext = os.path.splitext(file_info['path'])[1].lower()
            cluster_groups[cluster_id][ext].append(file_info)
        
        # Root at center
        root_pos = (0, 0)
        root_node = FileNode({'path': 'Root'}, QColor("#16213e"), 'root')
        root_node.setPos(*root_pos)
        self.scene.addItem(root_node)
        
        root_label = QGraphicsTextItem("All Files")
        root_label.setDefaultTextColor(QColor("#ffffff"))
        font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        root_label.setFont(font)
        root_label.setPos(-30, 35)
        self.scene.addItem(root_label)
        
        # CLUSTER level - inner ring
        cluster_radius = 220
        cluster_list = sorted(cluster_groups.keys())
        cluster_angle_step = 2 * math.pi / max(len(cluster_list), 1)
        
        for i, cluster_id in enumerate(cluster_list):
            angle = i * cluster_angle_step
            cluster_x = cluster_radius * math.cos(angle)
            cluster_y = cluster_radius * math.sin(angle)
            
            color = self.cluster_colors[cluster_id % len(self.cluster_colors)]
            cluster_node = FileNode({'path': f'C{cluster_id}'}, color, 'cluster')
            cluster_node.setPos(cluster_x, cluster_y)
            self.scene.addItem(cluster_node)
            
            # Edge from root to cluster
            self._add_edge(root_pos, (cluster_x, cluster_y), color.lighter(150), 2)
            
            # Cluster label
            cluster_name = f"Cluster {cluster_id}"
            if cluster_groups[cluster_id]:
                first_file = list(cluster_groups[cluster_id].values())[0][0]
                cluster_name = first_file.get('cluster_name', cluster_name)
            
            label = QGraphicsTextItem(cluster_name)
            label.setDefaultTextColor(color.lighter(160))
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            label.setFont(font)
            label_width = label.boundingRect().width()
            label.setPos(cluster_x - label_width/2, cluster_y + 28)
            self.scene.addItem(label)
            
            # TYPE level - middle ring (within cluster's arc)
            type_radius = 380
            types_in_cluster = sorted(cluster_groups[cluster_id].keys())
            
            # Calculate angle range for this cluster
            angle_start = angle - cluster_angle_step/2
            angle_end = angle + cluster_angle_step/2
            type_angle_step = (angle_end - angle_start) / max(len(types_in_cluster), 1)
            
            for j, ext in enumerate(types_in_cluster):
                type_angle = angle_start + (j + 0.5) * type_angle_step
                type_x = type_radius * math.cos(type_angle)
                type_y = type_radius * math.sin(type_angle)
                
                type_color = self.type_colors.get(ext, QColor("#95a5a6"))
                type_node = FileNode({'path': ext}, type_color, 'type')
                type_node.setPos(type_x, type_y)
                self.scene.addItem(type_node)
                
                # Edge from cluster to type
                self._add_edge((cluster_x, cluster_y), (type_x, type_y), color.lighter(130), 1.5)
                
                # Type label
                type_label = QGraphicsTextItem(ext.upper())
                type_label.setDefaultTextColor(type_color.lighter(140))
                font = QFont("Segoe UI", 7, QFont.Weight.Bold)
                type_label.setFont(font)
                type_label.setPos(type_x - 10, type_y + 18)
                self.scene.addItem(type_label)
                
                # FILE level - outer ring
                file_radius = 520
                files = cluster_groups[cluster_id][ext]
                file_count = len(files)
                file_angle_step = type_angle_step / max(file_count, 1)
                
                for k, file_info in enumerate(files[:15]):  # Limit for clarity
                    file_angle = angle_start + j * type_angle_step + k * file_angle_step
                    file_x = file_radius * math.cos(file_angle)
                    file_y = file_radius * math.sin(file_angle)
                    
                    file_node = FileNode(file_info, color, 'file')
                    file_node.setPos(file_x, file_y)
                    self.scene.addItem(file_node)
                    
                    # Edge from type to file
                    self._add_edge((type_x, type_y), (file_x, file_y), type_color.darker(110), 1)
        
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def _add_edge(self, start, end, color, width):
        """Add curved edge between nodes"""
        path = QPainterPath()
        path.moveTo(QPointF(*start))
        
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2
        
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
        edge.setZValue(0)
        edge.setOpacity(0.6)
        self.scene.addItem(edge)

    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1/zoom_factor, 1/zoom_factor)
