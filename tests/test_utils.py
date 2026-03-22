import pytest
import tempfile
from pathlib import Path

from src.shared.utils import format_size, format_datetime, highlight_text
from src.shared.config import Settings
from src.shared.models import FileInfo, DuplicateGroup, ScanResult


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"
    
    def test_kilobytes(self):
        assert format_size(1024) == "1.00 KB"
        assert format_size(1536) == "1.50 KB"
    
    def test_megabytes(self):
        assert format_size(1048576) == "1.00 MB"
        assert format_size(2621440) == "2.50 MB"
    
    def test_gigabytes(self):
        assert format_size(1073741824) == "1.00 GB"
    
    def test_zero(self):
        assert format_size(0) == "0 B"


class TestFormatDatetime:
    def test_valid_timestamp(self):
        from datetime import datetime
        
        timestamp = datetime(2024, 1, 15, 10, 30, 0).timestamp()
        result = format_datetime(timestamp)
        
        assert "2024" in result
    
    def test_zero_timestamp(self):
        result = format_datetime(0)
        assert result is not None


class TestHighlightText:
    def test_single_keyword(self):
        text = "This is a test file path"
        result = highlight_text(text, "test")
        
        assert "test" in result
        assert '<span style="background-color: #ffff00;">test</span>' in result
    
    def test_multiple_keywords(self):
        text = "This is a test file path"
        result = highlight_text(text, ["test", "file"])
        
        assert "test" in result
        assert "file" in result
    
    def test_case_insensitive(self):
        text = "This is a TEST file"
        result = highlight_text(text, "test", case_sensitive=False)
        
        assert "TEST" in result or "test" in result
    
    def test_no_match(self):
        text = "This is a file path"
        result = highlight_text(text, "xyz")
        
        assert result == text
    
    def test_empty_text(self):
        result = highlight_text("", "test")
        assert result == ""


class TestSettings:
    @pytest.fixture
    def settings(self, tmp_path):
        settings = Settings()
        settings._settings_file = str(tmp_path / "test.ini")
        from PyQt6.QtCore import QSettings
        settings._settings = QSettings(settings._settings_file, QSettings.Format.IniFormat)
        return settings
    
    def test_save_and_load_recent_directories(self, settings):
        directories = ["/path/one", "/path/two", "/path/three"]
        
        settings.recent_directories = directories
        loaded = settings.recent_directories
        
        assert loaded == directories
    
    def test_max_recent_directories(self, settings):
        directories = [f"/path/{i}" for i in range(15)]
        
        settings.recent_directories = directories
        loaded = settings.recent_directories
        
        assert len(loaded) <= 10
    
    def test_save_and_load_window_geometry(self, settings):
        from PyQt6.QtCore import QByteArray
        geometry = b"fake_geometry_data_12345"
        
        settings.window_geometry = geometry
        loaded = settings.window_geometry
        
        assert loaded == geometry


class TestModels:
    def test_file_info_creation(self):
        info = FileInfo(
            path="/test/file.txt",
            size=1024,
            mtime=1234567890.0,
            hash="abc123",
        )
        
        assert info.path == "/test/file.txt"
        assert info.size == 1024
        assert info.is_duplicate is False
    
    def test_duplicate_group(self):
        files = [
            FileInfo(path="/test/file1.txt", size=100, mtime=0, hash="abc"),
            FileInfo(path="/test/file2.txt", size=100, mtime=0, hash="abc"),
        ]
        
        group = DuplicateGroup(
            group_id=0,
            hash="abc",
            files=files,
            total_size=200,
            wasted_space=100,
        )
        
        assert len(group.files) == 2
        assert group.total_size == 200
    
    def test_scan_result(self):
        groups = [
            DuplicateGroup(
                group_id=0,
                hash="abc",
                files=[
                    FileInfo(path="/test/file1.txt", size=100, mtime=0, hash="abc"),
                    FileInfo(path="/test/file2.txt", size=100, mtime=0, hash="abc"),
                ],
                total_size=200,
                wasted_space=100,
            )
        ]
        
        result = ScanResult(
            directory="/test",
            total_files=10,
            duplicate_groups=groups,
            total_wasted=100,
        )
        
        assert result.total_files == 10
        assert len(result.duplicate_groups) == 1
    
    def test_file_info_to_dict(self):
        info = FileInfo(
            path="/test/file.txt",
            size=1024,
            mtime=1234567890.0,
            hash="abc123",
            is_duplicate=True,
        )
        
        data = info.to_dict()
        
        assert data["path"] == "/test/file.txt"
        assert data["size"] == 1024
        assert data["is_duplicate"] is True
        
        restored = FileInfo.from_dict(data)
        assert restored.path == info.path
        assert restored.hash == info.hash
