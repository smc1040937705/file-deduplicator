from typing import Optional, List, Callable
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool

from ..shared.models import ScanResult, ScanFilter, FileInfo, DuplicateGroup
from ..shared.config import Settings
from ..shared.constants import OPERATION_MOVE, OPERATION_DELETE
from ..scanner.scanner import ScannerManager
from ..storage.database import Database
from ..storage.models import ScanSnapshot, FileRecord, OperationLog
from ..operations.file_ops import FileOperator
from ..operations.exporter import ReportExporter


class AppController(QObject):
    scanStarted = pyqtSignal()
    scanProgress = pyqtSignal(int, int, str)
    hashProgress = pyqtSignal(int, int, str)
    scanFinished = pyqtSignal(object)
    scanError = pyqtSignal(str)
    
    operationStarted = pyqtSignal(str)
    operationProgress = pyqtSignal(int, int)
    operationFinished = pyqtSignal(str, int, int)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._settings = Settings()
        self._db = Database()
        self._scanner = ScannerManager(self)
        self._file_operator = FileOperator(self._db)
        self._current_result: Optional[ScanResult] = None
        self._current_snapshot_id: Optional[int] = None
        
        self._connect_signals()
    
    def _connect_signals(self):
        self._scanner.scan_started.connect(self.scanStarted.emit)
        self._scanner.scan_progress.connect(self.scanProgress.emit)
        self._scanner.hash_progress.connect(self.hashProgress.emit)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.scan_error.connect(self.scanError.emit)
    
    def start_scan(self, directory: str, filter_config: Optional[ScanFilter] = None):
        if not directory or not Path(directory).exists():
            self.scanError.emit(f"目录不存在: {directory}")
            return
        
        self._settings.add_recent_directory(directory)
        self._scanner.start_scan(directory, filter_config)
    
    def cancel_scan(self):
        self._scanner.cancel_scan()
    
    def _on_scan_finished(self, result: Optional[ScanResult]):
        if result is None:
            return
        
        self._current_result = result
        result.scan_time = datetime.now().timestamp()
        
        self._save_scan_result(result)
        
        self.scanFinished.emit(result)
    
    def _save_scan_result(self, result: ScanResult):
        snapshot = ScanSnapshot(
            directory=result.directory,
            scan_time=result.scan_time,
            total_files=result.total_files,
            duplicate_count=len(result.duplicate_groups),
            wasted_space=result.total_wasted,
        )
        
        files = []
        for group in result.duplicate_groups:
            for file_info in group.files:
                record = FileRecord(
                    path=file_info.path,
                    size=file_info.size,
                    mtime=file_info.mtime,
                    file_hash=file_info.hash or "",
                    is_duplicate=file_info.is_duplicate,
                    status=file_info.status,
                    group_id=group.group_id,
                )
                files.append(record)
        
        self._current_snapshot_id = self._db.save_snapshot(snapshot, files)
    
    def move_to_quarantine(self, files: List[FileInfo]):
        self.operationStarted.emit("移动到隔离区")
        
        success, fail = self._file_operator.batch_move_to_quarantine(
            files, self._current_snapshot_id,
            lambda c, t: self.operationProgress.emit(c, t)
        )
        
        self.operationFinished.emit("移动到隔离区", success, fail)
    
    def delete_files(self, files: List[FileInfo], use_trash: bool = True):
        self.operationStarted.emit("删除文件")
        
        success, fail = self._file_operator.batch_delete(
            files, self._current_snapshot_id, use_trash,
            lambda c, t: self.operationProgress.emit(c, t)
        )
        
        self.operationFinished.emit("删除文件", success, fail)
    
    def restore_file(self, quarantined_name: str):
        success, message = self._file_operator.restore_file(
            quarantined_name, self._current_snapshot_id
        )
        return success, message
    
    def get_quarantined_files(self) -> List[tuple]:
        return self._file_operator.quarantine.get_quarantined_files()
    
    def delete_from_quarantine(self, quarantined_name: str):
        return self._file_operator.quarantine.delete_permanently(quarantined_name)
    
    def clear_quarantine(self) -> tuple:
        return self._file_operator.quarantine.clear_quarantine()
    
    def export_report(self, format_type: str, output_path: str) -> bool:
        if not self._current_result:
            return False
        
        if format_type == "html":
            return ReportExporter.export_to_html(self._current_result, output_path)
        elif format_type == "csv":
            return ReportExporter.export_to_csv(self._current_result, output_path)
        elif format_type == "json":
            return ReportExporter.export_to_json(self._current_result, output_path)
        
        return False
    
    def open_file_location(self, file_path: str) -> bool:
        return FileOperator.open_file_location(file_path)
    
    def get_recent_directories(self) -> List[str]:
        return self._settings.recent_directories
    
    def get_window_geometry(self) -> bytes:
        return self._settings.window_geometry
    
    def save_window_geometry(self, geometry: bytes):
        self._settings.window_geometry = geometry
    
    def get_splitter_state(self) -> bytes:
        return self._settings.splitter_state
    
    def save_splitter_state(self, state: bytes):
        self._settings.splitter_state = state
    
    def get_recent_snapshots(self) -> List[ScanSnapshot]:
        return self._db.get_recent_snapshots()
    
    def get_operation_logs(self) -> List[OperationLog]:
        return self._db.get_operation_logs(self._current_snapshot_id)
    
    def sync_settings(self):
        self._settings.sync()
