import hashlib
from pathlib import Path
from typing import Optional, Callable
from ..shared.constants import DEFAULT_CHUNK_SIZE, HASH_ALGORITHM


class ChunkedHasher:
    def __init__(self, algorithm: str = HASH_ALGORITHM, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.algorithm = algorithm
        self.chunk_size = chunk_size
        self._hasher = hashlib.new(algorithm)
    
    def update(self, data: bytes):
        self._hasher.update(data)
    
    def hexdigest(self) -> str:
        return self._hasher.hexdigest()
    
    def reset(self):
        self._hasher = hashlib.new(self.algorithm)
    
    def hash_file(self, file_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> str:
        self.reset()
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        total_read = 0
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                self._hasher.update(chunk)
                total_read += len(chunk)
                if progress_callback:
                    progress_callback(total_read)
        
        return self._hasher.hexdigest()
    
    def hash_file_partial(self, file_path: str, partial_size: int = 1024 * 1024) -> str:
        self.reset()
        path = Path(file_path)
        
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'rb') as f:
            chunk = f.read(min(partial_size, self.chunk_size))
            self._hasher.update(chunk)
        
        return self._hasher.hexdigest()
    
    @staticmethod
    def quick_hash(file_path: str, algorithm: str = HASH_ALGORITHM) -> str:
        hasher = ChunkedHasher(algorithm)
        return hasher.hash_file(file_path)
