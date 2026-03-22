import pytest
import tempfile
import os
import shutil
from pathlib import Path
from datetime import datetime

from src.operations.file_ops import FileOperator, QuarantineManager
from src.operations.exporter import ReportExporter
from src.shared.models import FileInfo, DuplicateGroup, ScanResult


class TestFileOperator:
    @pytest.fixture
    def file_operator(self, tmp_path):
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        operator = FileOperator()
        operator.quarantine = QuarantineManager(str(quarantine_dir))
        return operator
    
    @pytest.fixture
    def sample_files(self, tmp_path):
        files = []
        for i in range(3):
            file_path = tmp_path / f"file{i}.txt"
            file_path.write_text(f"Content {i}")
            files.append(FileInfo(
                path=str(file_path),
                size=file_path.stat().st_size,
                mtime=file_path.stat().st_mtime,
            ))
        return files
    
    def test_move_to_quarantine(self, file_operator, sample_files):
        success, message = file_operator.move_to_quarantine(sample_files[0])
        
        assert success is True
        assert not os.path.exists(sample_files[0].path)
    
    def test_delete_file(self, file_operator, sample_files):
        success, message = file_operator.delete_file(sample_files[0], use_trash=False)
        
        assert success is True
        assert not os.path.exists(sample_files[0].path)
    
    def test_move_nonexistent_file(self, file_operator, tmp_path):
        file_info = FileInfo(path="/nonexistent/file.txt", size=0, mtime=0)
        success, message = file_operator.move_to_quarantine(file_info)
        
        assert success is False
    
    def test_batch_operations(self, file_operator, sample_files):
        success_count, fail_count = file_operator.batch_move_to_quarantine(sample_files)
        
        assert success_count == 3
        for f in sample_files:
            assert not os.path.exists(f.path)


class TestQuarantineManager:
    @pytest.fixture
    def quarantine_manager(self, tmp_path):
        quarantine_dir = tmp_path / "quarantine"
        quarantine_dir.mkdir()
        return QuarantineManager(str(quarantine_dir))
    
    @pytest.fixture
    def sample_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Test content")
        return str(file_path)
    
    def test_move_to_quarantine(self, quarantine_manager, sample_file):
        success, quarantined_path = quarantine_manager.move_to_quarantine(sample_file)
        
        assert success is True
        assert not os.path.exists(sample_file)
        assert os.path.exists(quarantined_path)
    
    def test_restore_from_quarantine(self, quarantine_manager, sample_file):
        success, quarantined_path = quarantine_manager.move_to_quarantine(sample_file)
        assert success is True
        
        quarantined_name = Path(quarantined_path).name
        success, restored_path = quarantine_manager.restore_from_quarantine(quarantined_name)
        
        assert success is True
        assert os.path.exists(sample_file)
    
    def test_get_quarantined_files(self, quarantine_manager, sample_file, tmp_path):
        file2 = tmp_path / "test2.txt"
        file2.write_text("Test content 2")
        
        quarantine_manager.move_to_quarantine(sample_file)
        quarantine_manager.move_to_quarantine(str(file2))
        
        quarantined = quarantine_manager.get_quarantined_files()
        
        assert len(quarantined) == 2
    
    def test_delete_permanently(self, quarantine_manager, sample_file):
        success, quarantined_path = quarantine_manager.move_to_quarantine(sample_file)
        assert success is True
        
        quarantined_name = Path(quarantined_path).name
        success, message = quarantine_manager.delete_permanently(quarantined_name)
        
        assert success is True
        quarantined = quarantine_manager.get_quarantined_files()
        assert len(quarantined) == 0


class TestReportExporter:
    @pytest.fixture
    def sample_result(self):
        files = [
            FileInfo(path="/test/file1.txt", size=1024, mtime=1234567890.0, hash="abc123", is_duplicate=True),
            FileInfo(path="/test/file2.txt", size=1024, mtime=1234567890.0, hash="abc123", is_duplicate=True),
        ]
        
        groups = [
            DuplicateGroup(
                group_id=0,
                hash="abc123",
                files=files,
                total_size=2048,
                wasted_space=1024,
            )
        ]
        
        return ScanResult(
            directory="/test/path",
            total_files=100,
            duplicate_groups=groups,
            total_wasted=1024,
        )
    
    def test_export_to_html(self, sample_result, tmp_path):
        output_path = tmp_path / "report.html"
        
        result = ReportExporter.export_to_html(sample_result, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        content = output_path.read_text(encoding='utf-8')
        assert "<html" in content.lower()
        assert "/test/file1.txt" in content
    
    def test_export_to_csv(self, sample_result, tmp_path):
        output_path = tmp_path / "report.csv"
        
        result = ReportExporter.export_to_csv(sample_result, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        content = output_path.read_text(encoding='utf-8')
        assert "file1.txt" in content
        assert "file2.txt" in content
    
    def test_export_to_json(self, sample_result, tmp_path):
        output_path = tmp_path / "report.json"
        
        result = ReportExporter.export_to_json(sample_result, str(output_path))
        
        assert result is True
        assert output_path.exists()
        
        import json
        data = json.loads(output_path.read_text(encoding='utf-8'))
        assert data["directory"] == "/test/path"
        assert len(data["duplicate_groups"]) == 1
