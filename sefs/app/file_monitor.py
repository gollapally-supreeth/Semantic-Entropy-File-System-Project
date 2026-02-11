from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from .config import Config

class SEFSEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_events = {}
        self.debounce_seconds = 1.0

    def on_moved(self, event):
        if event.is_directory:
            return
        if self._is_valid_file(event.dest_path):
            self._trigger('moved', event.dest_path)

    def on_created(self, event):
        if event.is_directory:
            return
        if self._is_valid_file(event.src_path):
            self._trigger('created', event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        # We might want to know if a tracked file was deleted
        self._trigger('deleted', event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._is_valid_file(event.src_path):
            self._trigger('modified', event.src_path)

    def _is_valid_file(self, path):
        import os
        ext = os.path.splitext(path)[1].lower()
        return ext in Config.EXTENSIONS

    def _trigger(self, event_type, path):
        # Simple debounce
        current_time = time.time()
        key = (event_type, path)
        if key in self.last_events:
            if current_time - self.last_events[key] < self.debounce_seconds:
                return
        
        self.last_events[key] = current_time
        self.callback(event_type, path)

class FileMonitor:
    def __init__(self, path, callback):
        self.path = path
        self.callback = callback
        self.observer = Observer()
        self.handler = SEFSEventHandler(callback)

    def start(self):
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
