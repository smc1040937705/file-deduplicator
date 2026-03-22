import os
import shutil
import send2trash
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from datetime import datetime
import platform

from ..shared.models import FileInfo, DuplicateGroup
from ..shared.constants import OPERATION_MOVE, OPERATION_DELETE, OPERATION_RESTORE
from ..storage.database import Database
from ..storage.models import OperationLog


class QuarantineManager:
    def __init__(self, quarantine_dir: Optional[str] = None):
        if quarantine_dir is None:
            app_data = Path.home() / ".file_deduplicator"
            quarantine_dir = str(app_data / "quarantine")
        
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_file = self.quarantine_dir / "manifest.txt"
        self._load_manifest()
    
    def _load_manifest(self):
        self._manifest: dict = {}
        if self._manifest_file.exists():
            try:
                with open(self._manifest_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '|' in line:
                            parts = line.split('|', 1)
                            if len(parts) == 2:
                                quarantined_name, original_path = parts
                                self._manifest[quarantined_name] = original_path
            except Exception:
                self._manifest = {}
    
    def _save_manifest(self):
        with open(self._manifest_file, 'w', encoding='utf-8') as f:
            for quarantined_name, original_path in self._manifest.items():
                f.write(f"{quarantined_name}|{original_path}\n")
    
    def _generate_quarantine_name(self, original_path: str) -> str:
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(original_path.encode()).hexdigest()[:8]
        original_name = Path(original_path).name
        return f"{timestamp}_{hash_part}_{original_name}"
    
    def move_to_quarantine(self, file_path: str) -> Tuple[bool, str]:
        try:
            source = Path(file_path)
            if not source.exists():
                return False, f"文件不存在: {file_path}"
            
            quarantined_name = self._generate_quarantine_name(file_path)
            target = self.quarantine_dir / quarantined_name
            
            shutil.move(str(source), str(target))
            
            self._manifest[quarantined_name] = file_path
            self._save_manifest()
            
            return True, str(target)
        except Exception as e:
            return False, str(e)
    
    def restore_from_quarantine(self, quarantined_name: str) -> Tuple[bool, str]:
        try:
            if quarantined_name not in self._manifest:
                return False, f"找不到隔离文件记录: {quarantined_name}"
            
            source = self.quarantine_dir / quarantined_name
            original_path = self._manifest[quarantined_name]
            target = Path(original_path)
            
            target.parent.mkdir(parents=True, exist_ok=True)
            
            if target.exists():
                return False, f"目标位置已存在文件: {original_path}"
            
            shutil.move(str(source), str(target))
            
            del self._manifest[quarantined_name]
            self._save_manifest()
            
            return True, original_path
        except Exception as e:
            return False, str(e)
    
    def delete_permanently(self, quarantined_name: str) -> Tuple[bool, str]:
        try:
            source = self.quarantine_dir / quarantined_name
            
            if source.exists():
                source.unlink()
            
            if quarantined_name in self._manifest:
                del self._manifest[quarantined_name]
                self._save_manifest()
            
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def get_quarantined_files(self) -> List[Tuple[str, str]]:
        result = []
        for name, original_path in self._manifest.items():
            file_path = self.quarantine_dir / name
            if file_path.exists():
                result.append((name, original_path))
        return result
    
    def clear_quarantine(self) -> Tuple[int, int]:
        success_count = 0
        fail_count = 0
        
        for name in list(self._manifest.keys()):
            success, _ = self.delete_permanently(name)
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        return success_count, fail_count


class FileOperator:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.quarantine = QuarantineManager()
    
    def move_to_quarantine(self, file_info: FileInfo, snapshot_id: Optional[int] = None) -> Tuple[bool, str]:
        success, message = self.quarantine.move_to_quarantine(file_info.path)
        
        log = OperationLog(
            snapshot_id=snapshot_id,
            operation_type=OPERATION_MOVE,
            file_path=file_info.path,
            target_path=message if success else None,
            operation_time=datetime.now().timestamp(),
            success=success,
            error_message="" if success else message,
        )
        self.db.add_operation_log(log)
        
        if success:
            file_info.status = "quarantined"
        
        return success, message
    
    def delete_file(self, file_info: FileInfo, snapshot_id: Optional[int] = None, 
                    use_trash: bool = True) -> Tuple[bool, str]:
        try:
            path = Path(file_info.path)
            if not path.exists():
                return False, f"文件不存在: {file_info.path}"
            
            if use_trash:
                send2trash.send2trash(str(path))
                message = ""
            else:
                path.unlink()
                message = ""
            
            log = OperationLog(
                snapshot_id=snapshot_id,
                operation_type=OPERATION_DELETE,
                file_path=file_info.path,
                operation_time=datetime.now().timestamp(),
                success=True,
            )
            self.db.add_operation_log(log)
            
            file_info.status = "deleted"
            return True, message
            
        except Exception as e:
            log = OperationLog(
                snapshot_id=snapshot_id,
                operation_type=OPERATION_DELETE,
                file_path=file_info.path,
                operation_time=datetime.now().timestamp(),
                success=False,
                error_message=str(e),
            )
            self.db.add_operation_log(log)
            
            return False, str(e)
    
    def restore_file(self, quarantined_name: str, snapshot_id: Optional[int] = None) -> Tuple[bool, str]:
        success, message = self.quarantine.restore_from_quarantine(quarantined_name)
        
        log = OperationLog(
            snapshot_id=snapshot_id,
            operation_type=OPERATION_RESTORE,
            file_path=message if success else "",
            target_path=quarantined_name,
            operation_time=datetime.now().timestamp(),
            success=success,
            error_message="" if success else message,
        )
        self.db.add_operation_log(log)
        
        return success, message
    
    def batch_move_to_quarantine(self, files: List[FileInfo], snapshot_id: Optional[int] = None,
                                  progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[int, int]:
        success_count = 0
        fail_count = 0
        
        for i, file_info in enumerate(files):
            success, _ = self.move_to_quarantine(file_info, snapshot_id)
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            if progress_callback:
                progress_callback(i + 1, len(files))
        
        return success_count, fail_count
    
    def batch_delete(self, files: List[FileInfo], snapshot_id: Optional[int] = None,
                     use_trash: bool = True,
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[int, int]:
        success_count = 0
        fail_count = 0
        
        for i, file_info in enumerate(files):
            success, _ = self.delete_file(file_info, snapshot_id, use_trash)
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            if progress_callback:
                progress_callback(i + 1, len(files))
        
        return success_count, fail_count
    
    @staticmethod
    def open_file_location(file_path: str) -> bool:
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            if platform.system() == "Windows":
                os.system(f'explorer /select,"{path}"')
            elif platform.system() == "Darwin":
                os.system(f'open -R "{path}"')
            else:
                os.system(f'xdg-open "{path.parent}"')
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def show_file_properties(file_path: str) -> bool:
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            if platform.system() == "Windows":
                os.system(f'powershell -command "Invoke-Item \'{path}\'"')
            elif platform.system() == "Darwin":
                os.system(f'open -R "{path}"')
            else:
                os.system(f'xdg-open "{path.parent}"')
            
            return True
        except Exception:
            return False
