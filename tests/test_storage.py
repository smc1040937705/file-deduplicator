import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from src.storage.database import Database
from src.storage.models import ScanSnapshot, FileRecord, OperationLog


class TestDatabase:
    @pytest.fixture
    def db(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db._initialized = False
        db.__init__(str(db_path))
        return db
    
    def test_save_and_get_snapshot(self, db):
        snapshot = ScanSnapshot(
            directory="/test/path",
            scan_time=datetime.now().timestamp(),
            total_files=100,
            duplicate_count=10,
            wasted_space=1024000,
        )
        
        files = []
        snapshot_id = db.save_snapshot(snapshot, files)
        assert snapshot_id is not None
        
        retrieved = db.get_snapshot(snapshot_id)
        assert retrieved is not None
        assert retrieved.directory == "/test/path"
        assert retrieved.total_files == 100
    
    def test_save_and_get_file_records(self, db):
        snapshot = ScanSnapshot(
            directory="/test/path",
            scan_time=datetime.now().timestamp(),
        )
        
        files = [
            FileRecord(
                path="/test/file1.txt",
                size=100,
                mtime=datetime.now().timestamp(),
                file_hash="abc123",
                is_duplicate=True,
                group_id=1,
            ),
            FileRecord(
                path="/test/file2.txt",
                size=100,
                mtime=datetime.now().timestamp(),
                file_hash="abc123",
                is_duplicate=True,
                group_id=1,
            ),
        ]
        
        snapshot_id = db.save_snapshot(snapshot, files)
        
        retrieved = db.get_files_by_snapshot(snapshot_id)
        assert len(retrieved) == 2
        assert retrieved[0].file_hash == "abc123"
    
    def test_save_and_get_operation_log(self, db):
        snapshot = ScanSnapshot(
            directory="/test/path",
            scan_time=datetime.now().timestamp(),
        )
        snapshot_id = db.save_snapshot(snapshot, [])
        
        log = OperationLog(
            snapshot_id=snapshot_id,
            operation_type="delete",
            file_path="/test/file.txt",
            operation_time=datetime.now().timestamp(),
            success=True,
        )
        
        log_id = db.add_operation_log(log)
        assert log_id is not None
        
        logs = db.get_operation_logs()
        assert len(logs) == 1
        assert logs[0].operation_type == "delete"
    
    def test_get_recent_snapshots(self, db):
        for i in range(5):
            snapshot = ScanSnapshot(
                directory=f"/test/path{i}",
                scan_time=datetime.now().timestamp(),
            )
            db.save_snapshot(snapshot, [])
        
        recent = db.get_recent_snapshots(limit=3)
        assert len(recent) == 3
    
    def test_delete_snapshot(self, db):
        snapshot = ScanSnapshot(
            directory="/test/path",
            scan_time=datetime.now().timestamp(),
        )
        snapshot_id = db.save_snapshot(snapshot, [])
        
        db.delete_snapshot(snapshot_id)
        
        retrieved = db.get_snapshot(snapshot_id)
        assert retrieved is None


class TestScanSnapshotPersistence:
    def test_snapshot_serialization(self):
        snapshot = ScanSnapshot(
            directory="/test/path",
            scan_time=1234567890.0,
            total_files=50,
            duplicate_count=5,
            wasted_space=2048000,
        )
        
        data = snapshot.to_dict()
        
        assert data["directory"] == "/test/path"
        assert data["total_files"] == 50
        
        restored = ScanSnapshot.from_dict(data)
        assert restored.directory == snapshot.directory
        assert restored.total_files == snapshot.total_files


class TestFileRecordPersistence:
    def test_file_record_serialization(self):
        record = FileRecord(
            path="/test/file.txt",
            size=1024,
            mtime=1234567890.0,
            file_hash="deadbeef" * 8,
            is_duplicate=True,
            group_id=1,
        )
        
        data = record.to_dict()
        
        assert data["path"] == "/test/file.txt"
        assert data["is_duplicate"] is True
        
        restored = FileRecord.from_dict(data)
        assert restored.path == record.path
        assert restored.file_hash == record.file_hash
