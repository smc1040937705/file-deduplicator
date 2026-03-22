import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from .models import FileRecord, ScanSnapshot, OperationLog
from ..shared.constants import DB_NAME


class Database:
    _instance: Optional['Database'] = None
    
    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return
        
        if db_path is None:
            app_data = Path.home() / ".file_deduplicator"
            app_data.mkdir(parents=True, exist_ok=True)
            db_path = str(app_data / DB_NAME)
        
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = True
        self._init_database()
    
    @contextmanager
    def _get_cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
        return self._connection
    
    def _init_database(self):
        with self._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directory TEXT NOT NULL,
                    scan_time REAL NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    duplicate_count INTEGER DEFAULT 0,
                    wasted_space INTEGER DEFAULT 0,
                    filter_config TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    path TEXT NOT NULL,
                    size INTEGER DEFAULT 0,
                    mtime REAL DEFAULT 0,
                    file_hash TEXT,
                    is_duplicate INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'normal',
                    group_id INTEGER,
                    FOREIGN KEY (snapshot_id) REFERENCES scan_snapshots(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    operation_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    target_path TEXT,
                    operation_time REAL NOT NULL,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY (snapshot_id) REFERENCES scan_snapshots(id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_records_hash ON file_records(file_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_records_snapshot ON file_records(snapshot_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_operation_logs_snapshot ON operation_logs(snapshot_id)
            """)
    
    def save_snapshot(self, snapshot: ScanSnapshot, files: List[FileRecord]) -> int:
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO scan_snapshots 
                (directory, scan_time, total_files, duplicate_count, wasted_space, filter_config)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot.directory,
                snapshot.scan_time,
                snapshot.total_files,
                snapshot.duplicate_count,
                snapshot.wasted_space,
                snapshot.filter_config,
            ))
            
            snapshot_id = cursor.lastrowid
            
            for file_record in files:
                file_record.snapshot_id = snapshot_id
                cursor.execute("""
                    INSERT INTO file_records
                    (snapshot_id, path, size, mtime, file_hash, is_duplicate, status, group_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_record.snapshot_id,
                    file_record.path,
                    file_record.size,
                    file_record.mtime,
                    file_record.file_hash,
                    1 if file_record.is_duplicate else 0,
                    file_record.status,
                    file_record.group_id,
                ))
            
            return snapshot_id
    
    def get_snapshot(self, snapshot_id: int) -> Optional[ScanSnapshot]:
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scan_snapshots WHERE id = ?
            """, (snapshot_id,))
            
            row = cursor.fetchone()
            if row:
                return ScanSnapshot(
                    id=row['id'],
                    directory=row['directory'],
                    scan_time=row['scan_time'],
                    total_files=row['total_files'],
                    duplicate_count=row['duplicate_count'],
                    wasted_space=row['wasted_space'],
                    filter_config=row['filter_config'],
                )
        return None
    
    def get_recent_snapshots(self, limit: int = 10) -> List[ScanSnapshot]:
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM scan_snapshots 
                ORDER BY scan_time DESC 
                LIMIT ?
            """, (limit,))
            
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(ScanSnapshot(
                    id=row['id'],
                    directory=row['directory'],
                    scan_time=row['scan_time'],
                    total_files=row['total_files'],
                    duplicate_count=row['duplicate_count'],
                    wasted_space=row['wasted_space'],
                    filter_config=row['filter_config'],
                ))
            
            return snapshots
    
    def get_files_by_snapshot(self, snapshot_id: int) -> List[FileRecord]:
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM file_records WHERE snapshot_id = ?
            """, (snapshot_id,))
            
            files = []
            for row in cursor.fetchall():
                files.append(FileRecord(
                    id=row['id'],
                    snapshot_id=row['snapshot_id'],
                    path=row['path'],
                    size=row['size'],
                    mtime=row['mtime'],
                    file_hash=row['file_hash'],
                    is_duplicate=bool(row['is_duplicate']),
                    status=row['status'],
                    group_id=row['group_id'],
                ))
            
            return files
    
    def update_file_status(self, file_id: int, status: str):
        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE file_records SET status = ? WHERE id = ?
            """, (status, file_id))
    
    def add_operation_log(self, log: OperationLog) -> int:
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO operation_logs
                (snapshot_id, operation_type, file_path, target_path, operation_time, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log.snapshot_id,
                log.operation_type,
                log.file_path,
                log.target_path,
                log.operation_time,
                1 if log.success else 0,
                log.error_message,
            ))
            
            return cursor.lastrowid
    
    def get_operation_logs(self, snapshot_id: Optional[int] = None) -> List[OperationLog]:
        with self._get_cursor() as cursor:
            if snapshot_id:
                cursor.execute("""
                    SELECT * FROM operation_logs WHERE snapshot_id = ? ORDER BY operation_time DESC
                """, (snapshot_id,))
            else:
                cursor.execute("""
                    SELECT * FROM operation_logs ORDER BY operation_time DESC
                """)
            
            logs = []
            for row in cursor.fetchall():
                logs.append(OperationLog(
                    id=row['id'],
                    snapshot_id=row['snapshot_id'],
                    operation_type=row['operation_type'],
                    file_path=row['file_path'],
                    target_path=row['target_path'],
                    operation_time=row['operation_time'],
                    success=bool(row['success']),
                    error_message=row['error_message'],
                ))
            
            return logs
    
    def delete_snapshot(self, snapshot_id: int):
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM file_records WHERE snapshot_id = ?", (snapshot_id,))
            cursor.execute("DELETE FROM operation_logs WHERE snapshot_id = ?", (snapshot_id,))
            cursor.execute("DELETE FROM scan_snapshots WHERE id = ?", (snapshot_id,))
    
    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
