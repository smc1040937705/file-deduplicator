from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import os


@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float
    hash: Optional[str] = None
    is_duplicate: bool = False
    status: str = "normal"
    
    @property
    def filename(self) -> str:
        return os.path.basename(self.path)
    
    @property
    def directory(self) -> str:
        return os.path.dirname(self.path)
    
    @property
    def extension(self) -> str:
        return os.path.splitext(self.filename)[1].lower()
    
    @property
    def modified_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.mtime)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "hash": self.hash,
            "is_duplicate": self.is_duplicate,
            "status": self.status,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileInfo':
        return cls(
            path=data["path"],
            size=data["size"],
            mtime=data["mtime"],
            hash=data.get("hash"),
            is_duplicate=data.get("is_duplicate", False),
            status=data.get("status", "normal"),
        )


class DuplicateGroup:
    def __init__(self, group_id: int = 0, hash: str = "", files: List[FileInfo] = None, 
                 selected_index: int = 0, total_size: int = 0, wasted_space: int = 0):
        self.group_id = group_id
        self.hash = hash
        self.files = files if files is not None else []
        self.selected_index = selected_index
        self._total_size = total_size if total_size > 0 else 0
        self._wasted_space = wasted_space if wasted_space > 0 else 0
    
    @property
    def total_size(self) -> int:
        if self._total_size == 0 and self.files:
            return self.files[0].size if self.files else 0
        return self._total_size
    
    @property
    def count(self) -> int:
        return len(self.files)
    
    @property
    def wasted_space(self) -> int:
        if self._wasted_space > 0:
            return self._wasted_space
        if self.count <= 1:
            return 0
        return self.total_size * (self.count - 1)
    
    @property
    def selected_file(self) -> Optional[FileInfo]:
        if 0 <= self.selected_index < len(self.files):
            return self.files[self.selected_index]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.hash,
            "files": [f.to_dict() for f in self.files],
            "selected_index": self.selected_index,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DuplicateGroup':
        return cls(
            hash=data["hash"],
            files=[FileInfo.from_dict(f) for f in data["files"]],
            selected_index=data.get("selected_index", 0),
        )


@dataclass
class ScanResult:
    directory: str = ""
    total_files: int = 0
    total_size: int = 0
    total_wasted: int = 0
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    scan_time: float = 0.0
    error_count: int = 0
    skipped_count: int = 0
    
    @property
    def duplicate_count(self) -> int:
        return sum(g.count for g in self.duplicate_groups)
    
    @property
    def wasted_space(self) -> int:
        return sum(g.wasted_space for g in self.duplicate_groups)
    
    @property
    def group_count(self) -> int:
        return len(self.duplicate_groups)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_size": self.total_size,
            "duplicate_groups": [g.to_dict() for g in self.duplicate_groups],
            "scan_time": self.scan_time,
            "error_count": self.error_count,
            "skipped_count": self.skipped_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        return cls(
            total_files=data.get("total_files", 0),
            total_size=data.get("total_size", 0),
            duplicate_groups=[DuplicateGroup.from_dict(g) for g in data.get("duplicate_groups", [])],
            scan_time=data.get("scan_time", 0.0),
            error_count=data.get("error_count", 0),
            skipped_count=data.get("skipped_count", 0),
        )


@dataclass
class ScanFilter:
    file_types: List[str] = field(default_factory=lambda: ["all"])
    min_size: int = 0
    max_size: int = 0
    date_filter: Optional[str] = None
    extensions: List[str] = field(default_factory=list)
    skip_hidden: bool = True
    skip_system: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_types": self.file_types,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "date_filter": self.date_filter,
            "extensions": self.extensions,
            "skip_hidden": self.skip_hidden,
            "skip_system": self.skip_system,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanFilter':
        return cls(
            file_types=data.get("file_types", ["all"]),
            min_size=data.get("min_size", 0),
            max_size=data.get("max_size", 0),
            date_filter=data.get("date_filter"),
            extensions=data.get("extensions", []),
            skip_hidden=data.get("skip_hidden", True),
            skip_system=data.get("skip_system", True),
        )
