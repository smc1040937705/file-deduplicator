import pytest
import tempfile
import os
from pathlib import Path
import shutil

from src.scanner.hasher import ChunkedHasher
from src.scanner.scanner import FileScanner
from src.shared.models import ScanFilter


class TestChunkedHasher:
    def test_hash_small_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        hasher = ChunkedHasher()
        result = hasher.hash_file(str(test_file))
        
        assert result is not None
        assert len(result) == 64
    
    def test_hash_empty_file(self, tmp_path):
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")
        
        hasher = ChunkedHasher()
        result = hasher.hash_file(str(test_file))
        
        assert result is not None
        assert len(result) == 64
    
    def test_hash_nonexistent_file(self, tmp_path):
        hasher = ChunkedHasher()
        
        with pytest.raises(FileNotFoundError):
            hasher.hash_file(str(tmp_path / "nonexistent.txt"))
    
    def test_same_content_same_hash(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        content = "Same content for both files"
        file1.write_text(content)
        file2.write_text(content)
        
        hasher = ChunkedHasher()
        hash1 = hasher.hash_file(str(file1))
        hash2 = hasher.hash_file(str(file2))
        
        assert hash1 == hash2
    
    def test_different_content_different_hash(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        file1.write_text("Content A")
        file2.write_text("Content B")
        
        hasher = ChunkedHasher()
        hash1 = hasher.hash_file(str(file1))
        hash2 = hasher.hash_file(str(file2))
        
        assert hash1 != hash2


class TestFileScanner:
    @pytest.fixture
    def sample_directory(self, tmp_path):
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        (dir1 / "file1.txt").write_text("Content A")
        (dir1 / "file2.txt").write_text("Content B")
        (dir2 / "file3.txt").write_text("Content A")
        (dir2 / "file4.txt").write_text("Content C")
        
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "hidden_file.txt").write_text("Hidden content")
        
        return tmp_path
    
    def test_scan_directory_basic(self, sample_directory):
        scanner = FileScanner()
        files = scanner.scan_directory(str(sample_directory))
        
        assert len(files) >= 4
    
    def test_scan_directory_skip_hidden(self, sample_directory):
        filter_config = ScanFilter(skip_hidden=True)
        scanner = FileScanner(filter_config)
        files = scanner.scan_directory(str(sample_directory))
        
        for f in files:
            assert ".hidden" not in f.path
    
    def test_scan_directory_filter_by_size(self, sample_directory):
        for f in sample_directory.rglob("*.txt"):
            if f.name == "file1.txt":
                f.write_text("A" * 10000)
        
        filter_config = ScanFilter(min_size=5000)
        scanner = FileScanner(filter_config)
        files = scanner.scan_directory(str(sample_directory))
        
        assert len(files) == 1
        assert files[0].size >= 5000
    
    def test_find_duplicates(self, sample_directory):
        scanner = FileScanner()
        files = scanner.scan_directory(str(sample_directory))
        scanner.compute_hashes(files)
        duplicates = scanner.find_duplicates(files)
        
        assert len(duplicates) >= 1
        
        found_pair = False
        for group in duplicates:
            paths = [f.path for f in group.files]
            if any("file1.txt" in p for p in paths) and any("file3.txt" in p for p in paths):
                found_pair = True
                break
        
        assert found_pair
    
    def test_cancel_scan(self, sample_directory):
        scanner = FileScanner()
        scanner.cancel()
        
        files = scanner.scan_directory(str(sample_directory))
        
        assert len(files) == 0


class TestDirectoryTraversal:
    @pytest.fixture
    def nested_directory(self, tmp_path):
        level1 = tmp_path / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"
        
        level1.mkdir()
        level2.mkdir()
        level3.mkdir()
        
        (tmp_path / "root.txt").write_text("root")
        (level1 / "l1.txt").write_text("level1")
        (level2 / "l2.txt").write_text("level2")
        (level3 / "l3.txt").write_text("level3")
        
        return tmp_path
    
    def test_recursive_traversal(self, nested_directory):
        scanner = FileScanner()
        files = scanner.scan_directory(str(nested_directory))
        
        assert len(files) == 4
        
        depths = set()
        for f in files:
            depth = f.path.count(os.sep) - str(nested_directory).count(os.sep)
            depths.add(depth)
        
        assert len(depths) == 4
    
    def test_empty_directory(self, tmp_path):
        scanner = FileScanner()
        files = scanner.scan_directory(str(tmp_path))
        
        assert len(files) == 0
