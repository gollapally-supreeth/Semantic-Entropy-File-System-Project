from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QSplitter)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from .graph_view import GraphView
from .log_panel import LogPanel

class MainWindow(QMainWindow):
    start_monitoring_signal = pyqtSignal(str)
    stop_monitoring_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Semantic Entropy File System")
        self.resize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar
        top_bar = QHBoxLayout()
        self.root_btn = QPushButton("Select Root Directory")
        self.root_btn.clicked.connect(self.select_root)
        self.root_label = QLabel("No directory selected")
        
        self.toggle_btn = QPushButton("Start Monitoring")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.toggle_monitoring)
        self.toggle_btn.setEnabled(False)

        top_bar.addWidget(self.root_btn)
        top_bar.addWidget(self.root_label)
        top_bar.addWidget(self.toggle_btn)
        main_layout.addLayout(top_bar)

        # Splitter for Graph and Log
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.graph_view = GraphView()
        splitter.addWidget(self.graph_view)
        
        self.log_panel = LogPanel()
        splitter.addWidget(self.log_panel)
        
        main_layout.addWidget(splitter)
        
        self.root_path = None
        self.is_monitoring = False

    def select_root(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Root Directory")
        if folder:
            self.root_path = folder
            self.root_label.setText(folder)
            self.toggle_btn.setEnabled(True)
            self.log_panel.add_log(f"Selected root: {folder}")

    def toggle_monitoring(self):
        if self.toggle_btn.isChecked():
            self.is_monitoring = True
            self.toggle_btn.setText("Stop Monitoring")
            self.root_btn.setEnabled(False)
            self.start_monitoring_signal.emit(self.root_path)
            self.log_panel.add_log("Monitoring started.")
        else:
            self.is_monitoring = False
            self.toggle_btn.setText("Start Monitoring")
            self.root_btn.setEnabled(True)
            self.stop_monitoring_signal.emit()
            self.log_panel.add_log("Monitoring stopped.")

    @pyqtSlot(dict)
    def update_ui_state(self, state):
        # state probably contains lists of files and coords
        # This will be connected to the worker
        pass
