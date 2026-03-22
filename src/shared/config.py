from PyQt6.QtCore import QSettings, QByteArray
from typing import List, Optional
import json
from pathlib import Path


class Settings:
    _instance: Optional['Settings'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = QSettings("FileDeduplicator", "FileDeduplicator")
        return cls._instance
    
    @property
    def recent_directories(self) -> List[str]:
        value = self._settings.value("recent_directories", "[]")
        if isinstance(value, str):
            return json.loads(value)
        return []
    
    @recent_directories.setter
    def recent_directories(self, dirs: List[str]):
        dirs = dirs[:10]
        self._settings.setValue("recent_directories", json.dumps(dirs))
    
    def add_recent_directory(self, path: str):
        dirs = self.recent_directories
        if path in dirs:
            dirs.remove(path)
        dirs.insert(0, path)
        dirs = dirs[:10]
        self.recent_directories = dirs
    
    @property
    def last_scan_directory(self) -> Optional[str]:
        return self._settings.value("last_scan_directory")
    
    @last_scan_directory.setter
    def last_scan_directory(self, path: Optional[str]):
        self._settings.setValue("last_scan_directory", path)
    
    @property
    def window_geometry(self) -> Optional[bytes]:
        geometry = self._settings.value("window_geometry")
        if isinstance(geometry, QByteArray):
            return bytes(geometry)
        return None
    
    @window_geometry.setter
    def window_geometry(self, geometry: bytes):
        self._settings.setValue("window_geometry", QByteArray(geometry))
    
    @property
    def window_state(self) -> Optional[bytes]:
        state = self._settings.value("window_state")
        if isinstance(state, QByteArray):
            return bytes(state)
        return None
    
    @window_state.setter
    def window_state(self, state: bytes):
        self._settings.setValue("window_state", QByteArray(state))
    
    @property
    def quarantine_directory(self) -> Optional[str]:
        return self._settings.value("quarantine_directory")
    
    @quarantine_directory.setter
    def quarantine_directory(self, path: Optional[str]):
        self._settings.setValue("quarantine_directory", path)
    
    @property
    def chunk_size(self) -> int:
        return int(self._settings.value("chunk_size", 8 * 1024 * 1024))
    
    @chunk_size.setter
    def chunk_size(self, size: int):
        self._settings.setValue("chunk_size", size)
    
    @property
    def skip_hidden_files(self) -> bool:
        return self._settings.value("skip_hidden_files", True, type=bool)
    
    @skip_hidden_files.setter
    def skip_hidden_files(self, skip: bool):
        self._settings.setValue("skip_hidden_files", skip)
    
    @property
    def skip_system_files(self) -> bool:
        return self._settings.value("skip_system_files", True, type=bool)
    
    @skip_system_files.setter
    def skip_system_files(self, skip: bool):
        self._settings.setValue("skip_system_files", skip)
    
    @property
    def min_file_size(self) -> int:
        return int(self._settings.value("min_file_size", 0))
    
    @min_file_size.setter
    def min_file_size(self, size: int):
        self._settings.setValue("min_file_size", size)
    
    @property
    def max_file_size(self) -> int:
        return int(self._settings.value("max_file_size", 0))
    
    @max_file_size.setter
    def max_file_size(self, size: int):
        self._settings.setValue("max_file_size", size)
    
    @property
    def file_type_filter(self) -> str:
        return self._settings.value("file_type_filter", "all")
    
    @file_type_filter.setter
    def file_type_filter(self, filter_type: str):
        self._settings.setValue("file_type_filter", filter_type)
    
    @property
    def split_header_state(self) -> Optional[bytes]:
        state = self._settings.value("split_header_state")
        if isinstance(state, QByteArray):
            return bytes(state)
        return None
    
    @split_header_state.setter
    def split_header_state(self, state: bytes):
        self._settings.setValue("split_header_state", QByteArray(state))
    
    @property
    def splitter_state(self) -> Optional[bytes]:
        state = self._settings.value("splitter_state")
        if isinstance(state, QByteArray):
            return bytes(state)
        return None
    
    @splitter_state.setter
    def splitter_state(self, state: bytes):
        self._settings.setValue("splitter_state", QByteArray(state))
    
    def sync(self):
        self._settings.sync()
