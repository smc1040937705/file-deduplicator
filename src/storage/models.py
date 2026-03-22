from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class FileRecord:
    id: Optional[int] = None
    snapshot_id: Optional[int] = None
    path: str = ""
    size: int = 0
    mtime: float = 0.0
    file_hash: str = ""
    is_duplicate: bool = False
    status: str = "normal"
    group_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "file_hash": self.file_hash,
            "is_duplicate": self.is_duplicate,
            "status": self.status,
            "group_id": self.group_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileRecord':
        return cls(
            id=data.get("id"),
            snapshot_id=data.get("snapshot_id"),
            path=data.get("path", ""),
            size=data.get("size", 0),
            mtime=data.get("mtime", 0.0),
            file_hash=data.get("file_hash", ""),
            is_duplicate=data.get("is_duplicate", False),
            status=data.get("status", "normal"),
            group_id=data.get("group_id"),
        )


@dataclass
class ScanSnapshot:
    id: Optional[int] = None
    directory: str = ""
    scan_time: float = 0.0
    total_files: int = 0
    duplicate_count: int = 0
    wasted_space: int = 0
    filter_config: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "directory": self.directory,
            "scan_time": self.scan_time,
            "total_files": self.total_files,
            "duplicate_count": self.duplicate_count,
            "wasted_space": self.wasted_space,
            "filter_config": self.filter_config,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanSnapshot':
        return cls(
            id=data.get("id"),
            directory=data.get("directory", ""),
            scan_time=data.get("scan_time", 0.0),
            total_files=data.get("total_files", 0),
            duplicate_count=data.get("duplicate_count", 0),
            wasted_space=data.get("wasted_space", 0),
            filter_config=data.get("filter_config", ""),
        )


@dataclass
class OperationLog:
    id: Optional[int] = None
    snapshot_id: Optional[int] = None
    operation_type: str = ""
    file_path: str = ""
    target_path: Optional[str] = None
    operation_time: float = 0.0
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "operation_type": self.operation_type,
            "file_path": self.file_path,
            "target_path": self.target_path,
            "operation_time": self.operation_time,
            "success": self.success,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationLog':
        return cls(
            id=data.get("id"),
            snapshot_id=data.get("snapshot_id"),
            operation_type=data.get("operation_type", ""),
            file_path=data.get("file_path", ""),
            target_path=data.get("target_path"),
            operation_time=data.get("operation_time", 0.0),
            success=data.get("success", True),
            error_message=data.get("error_message", ""),
        )
