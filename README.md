# 文件去重整理器 (File Deduplicator)

一个基于 Python + PyQt6 构建的本地文件去重工具，帮助您扫描、识别和管理重复文件。

## 功能特性

- **智能扫描**: 递归扫描目录，按文件哈希分组重复项
- **分块哈希**: 采用分块计算方式，避免大文件内存峰值
- **灵活过滤**: 支持按文件类型、大小、修改时间过滤
- **批量操作**: 支持批量移动到隔离区或永久删除
- **安全隔离**: 隔离区管理，支持恢复误删文件
- **搜索高亮**: 搜索文件名与路径，关键词高亮显示
- **报告导出**: 导出扫描报告为 HTML、CSV 或 JSON 格式
- **状态持久化**: 窗口状态、最近扫描目录自动保存

## 系统要求

- Python >= 3.10
- PyQt6 >= 6.5.0

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd test

# 安装依赖
pip install -e .

# 或者手动安装依赖
pip install PyQt6 send2trash
```

## 运行

```bash
python main.py
```

## 项目结构

```
src/
├── app/                    # UI层
│   ├── main_window.py      # 主窗口
│   ├── controllers.py      # 控制器（业务逻辑）
│   └── widgets.py          # UI组件
├── scanner/                # 扫描模块
│   ├── scanner.py          # 文件扫描器
│   └── hasher.py           # 分块哈希计算
├── storage/                # 存储模块
│   ├── database.py         # SQLite数据库操作
│   └── models.py           # 数据模型
├── operations/             # 操作模块
│   ├── file_ops.py         # 文件操作/隔离区管理
│   └── exporter.py         # 报告导出
└── shared/                 # 共享模块
    ├── constants.py        # 常量定义
    ├── config.py           # 配置管理
    ├── utils.py            # 工具函数
    └── models.py           # 数据模型

tests/                      # 测试用例
├── test_scanner.py         # 扫描器测试
├── test_storage.py         # 存储测试
├── test_operations.py      # 操作测试
└── test_utils.py           # 工具测试
```

## 使用说明

### 1. 选择扫描目录

点击"浏览..."按钮选择要扫描的目录，或直接输入目录路径。

### 2. 设置过滤条件

在左侧过滤面板中设置：
- **文件类型**: 选择特定类型或全部文件
- **文件大小**: 设置最小/最大文件大小
- **修改时间**: 筛选今天/本周/本月修改的文件
- **选项**: 是否跳过隐藏文件和系统文件

### 3. 开始扫描

点击"开始扫描"按钮，程序会：
1. 递归遍历目录中的所有文件
2. 计算每个文件的哈希值
3. 按哈希值分组重复文件

### 4. 处理重复文件

扫描完成后：
- 勾选要处理的文件
- 点击"移动到隔离区"将文件移入隔离区
- 点击"永久删除"直接删除文件

### 5. 管理隔离区

切换到"隔离区"标签页：
- 查看已隔离的文件
- 恢复误删的文件
- 清空隔离区

### 6. 导出报告

点击"文件" -> "导出报告"，选择格式：
- HTML: 美观的网页报告
- CSV: 表格格式，便于数据分析
- JSON: 结构化数据，便于程序处理

## 技术要点

### 分块哈希计算

为避免大文件导致内存峰值，采用分块读取计算哈希：

```python
def hash_file(self, file_path: str, chunk_size: int = 8 * 1024 * 1024) -> str:
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()
```

### 多线程扫描

使用 QThreadPool 实现后台扫描，支持中断：

```python
class ScanWorker(QRunnable):
    def run(self):
        # 扫描逻辑
        pass
    
    def cancel(self):
        self._scanner.cancel()
```

### 数据持久化

- 使用 SQLite 存储扫描快照和操作日志
- 使用 QSettings 存储窗口状态和用户偏好

## 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest tests/

# 带覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

## 许可证

MIT License
