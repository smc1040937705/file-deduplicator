import os
import stat
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set
from collections import defaultdict
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QThreadPool

from ..shared.models import FileInfo, DuplicateGroup, ScanResult, ScanFilter
from ..shared.constants import SYSTEM_FOLDERS
from .hasher import ChunkedHasher


class FileScanner:
    def __init__(self, filter_config: Optional[ScanFilter] = None):
        self.filter = filter_config or ScanFilter()
        self.hasher = ChunkedHasher()
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def reset(self):
        self._cancelled = False
    
    def _should_skip(self, path: Path) -> bool:
        # Check if any parent directory in the path should be skipped
        if self.filter.skip_hidden:
            try:
                # Check if path or any parent starts with '.'
                for part in path.parts:
                    if part.startswith('.'):
                        return True
                # On Windows, check hidden attribute
                if os.name == 'nt':
                    try:
                        if path.stat().st_file_attributes & 2:
                            return True
                    except (OSError, AttributeError):
                        pass
            except (OSError, AttributeError):
                pass
        
        if self.filter.skip_system:
            try:
                if os.name == 'nt':
                    try:
                        attrs = path.stat().st_file_attributes
                        if attrs & (stat.FILE_ATTRIBUTE_SYSTEM | stat.FILE_ATTRIBUTE_TEMPORARY):
                            return True
                    except (OSError, AttributeError):
                        pass
                # Check if path name is in system folders
                if path.name in SYSTEM_FOLDERS:
                    return True
            except (OSError, AttributeError):
                pass
        
        return False
    
    def _matches_filter(self, path: Path) -> bool:
        if self.filter.extensions:
            ext = path.suffix.lower()
            if ext not in [e.lower() for e in self.filter.extensions]:
                return False
        
        try:
            stat_info = path.stat()
            size = stat_info.st_size
            mtime = stat_info.st_mtime
            
            if self.filter.min_size > 0 and size < self.filter.min_size:
                return False
            if self.filter.max_size > 0 and size > self.filter.max_size:
                return False
            
            if self.filter.date_filter:
                file_time = datetime.fromtimestamp(mtime)
                now = datetime.now()
                if self.filter.date_filter == "today":
                    if file_time.date() != now.date():
                        return False
                elif self.filter.date_filter == "week":
                    if file_time < now - timedelta(days=7):
                        return False
                elif self.filter.date_filter == "month":
                    if file_time < now - timedelta(days=30):
                        return False
        except OSError:
            return False
        
        return True
    
    def scan_directory(self, directory: str, 
                       progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[FileInfo]:
        # Only reset if not already cancelled (to allow pre-cancellation)
        if not self._cancelled:
            self.reset()
        files = []
        root_path = Path(directory)
        
        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        total_files = 0
        processed = 0
        
        for _ in root_path.rglob('*'):
            if self._cancelled:
                break
            total_files += 1
        
        for path in root_path.rglob('*'):
            if self._cancelled:
                break
            
            if not path.is_file():
                continue
            
            if self._should_skip(path):
                continue
            
            if not self._matches_filter(path):
                continue
            
            try:
                stat_info = path.stat()
                file_info = FileInfo(
                    path=str(path),
                    size=stat_info.st_size,
                    mtime=stat_info.st_mtime,
                )
                files.append(file_info)
            except OSError:
                continue
            
            processed += 1
            if progress_callback and processed % 10 == 0:
                progress_callback(processed, total_files, str(path))
        
        return files
    
    def compute_hashes(self, files: List[FileInfo],
                       progress_callback: Optional[Callable[[int, int, str], None]] = None) -> None:
        total = len(files)
        for i, file_info in enumerate(files):
            if self._cancelled:
                break
            
            try:
                file_info.hash = self.hasher.hash_file(file_info.path)
            except (OSError, IOError):
                file_info.hash = None
            
            if progress_callback:
                progress_callback(i + 1, total, file_info.path)
    
    def find_duplicates(self, files: List[FileInfo]) -> List[DuplicateGroup]:
        hash_groups: Dict[str, List[FileInfo]] = defaultdict(list)
        
        for file_info in files:
            if file_info.hash:
                hash_groups[file_info.hash].append(file_info)
        
        duplicates = []
        group_id = 0
        
        for file_hash, group_files in hash_groups.items():
            if len(group_files) > 1:
                total_size = sum(f.size for f in group_files)
                wasted = total_size - group_files[0].size
                
                for f in group_files:
                    f.is_duplicate = True
                
                dup_group = DuplicateGroup(
                    hash=file_hash,
                    files=group_files,
                    group_id=group_id,
                    total_size=total_size,
                    wasted_space=wasted,
                )
                duplicates.append(dup_group)
                group_id += 1
        
        duplicates.sort(key=lambda g: g.wasted_space, reverse=True)
        return duplicates


class ScanWorkerSignals(QObject):
    started = pyqtSignal()
    progress = pyqtSignal(int, int, str)
    hashing_progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class ScanWorker(QRunnable):
    def __init__(self, directory: str, filter_config: Optional[ScanFilter] = None):
        super().__init__()
        self.directory = directory
        self.filter_config = filter_config
        self.signals = ScanWorkerSignals()
        self._scanner: Optional[FileScanner] = None
    
    def run(self):
        self.signals.started.emit()
        
        try:
            self._scanner = FileScanner(self.filter_config)
            
            def scan_progress(current: int, total: int, path: str):
                self.signals.progress.emit(current, total, path)
            
            files = self._scanner.scan_directory(self.directory, scan_progress)
            
            if not self._scanner._cancelled:
                def hash_progress(current: int, total: int, path: str):
                    self.signals.hashing_progress.emit(current, total, path)
                
                self._scanner.compute_hashes(files, hash_progress)
            
            if not self._scanner._cancelled:
                duplicates = self._scanner.find_duplicates(files)
                result = ScanResult(
                    directory=self.directory,
                    total_files=len(files),
                    duplicate_groups=duplicates,
                    total_wasted=sum(g.wasted_space for g in duplicates),
                )
                self.signals.finished.emit(result)
            else:
                self.signals.finished.emit(None)
                
        except Exception as e:
            self.signals.error.emit(str(e))
    
    def cancel(self):
        if self._scanner:
            self._scanner.cancel()


class ScannerManager(QObject):
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int, str)
    hash_progress = pyqtSignal(int, int, str)
    scan_finished = pyqtSignal(object)
    scan_error = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._thread_pool = QThreadPool.globalInstance()
        self._current_worker: Optional[ScanWorker] = None
    
    def start_scan(self, directory: str, filter_config: Optional[ScanFilter] = None):
        self.cancel_scan()
        
        worker = ScanWorker(directory, filter_config)
        worker.signals.started.connect(self.scan_started.emit)
        worker.signals.progress.connect(self.scan_progress.emit)
        worker.signals.hashing_progress.connect(self.hash_progress.emit)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self.scan_error.emit)
        
        self._current_worker = worker
        self._thread_pool.start(worker)
    
    def cancel_scan(self):
        if self._current_worker:
            self._current_worker.cancel()
            self._current_worker = None
    
    def _on_finished(self, result):
        self._current_worker = None
        self.scan_finished.emit(result)
