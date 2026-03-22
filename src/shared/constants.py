DB_NAME = "file_deduplicator.db"

APP_NAME = "FileDeduplicator"
APP_VERSION = "1.0.0"
ORGANIZATION = "FileDeduplicator"

DEFAULT_CHUNK_SIZE = 1024 * 1024 * 8
HASH_ALGORITHM = "sha256"
MAX_RECENT_DIRS = 10

FILE_TYPE_FILTERS = {
    "all": "*",
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico"],
    "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "documents": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".rb"],
}

SIZE_FILTERS = [
    ("all", 0, float('inf')),
    ("tiny", 0, 1024),
    ("small", 1024, 1024 * 1024),
    ("medium", 1024 * 1024, 100 * 1024 * 1024),
    ("large", 100 * 1024 * 1024, 1024 * 1024 * 1024),
    ("huge", 1024 * 1024 * 1024, float('inf')),
]

DATE_FILTERS = {
    "all": None,
    "today": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}

QUARANTINE_DIR_NAME = ".deduplicator_quarantine"

SYSTEM_FOLDERS = {
    "System Volume Information",
    "$RECYCLE.BIN",
    "Recovery",
    "Config.Msi",
    "Windows",
    "Program Files",
    "Program Files (x86)",
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "node_modules",
    ".idea",
    ".vscode",
}

SCAN_STATUS_PENDING = "pending"
SCAN_STATUS_RUNNING = "running"
SCAN_STATUS_COMPLETED = "completed"
SCAN_STATUS_CANCELLED = "cancelled"
SCAN_STATUS_ERROR = "error"

FILE_STATUS_NORMAL = "normal"
FILE_STATUS_QUARANTINED = "quarantined"
FILE_STATUS_DELETED = "deleted"

OPERATION_MOVE = "move"
OPERATION_DELETE = "delete"
OPERATION_RESTORE = "restore"
