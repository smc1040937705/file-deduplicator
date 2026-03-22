from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter,
    QGroupBox, QCheckBox, QComboBox, QSpinBox, QProgressBar,
    QFileDialog, QMessageBox, QMenu, QHeaderView, QTabWidget,
    QTextEdit, QDialog, QDialogButtonBox, QFormLayout, QListWidget,
    QListWidgetItem, QAbstractItemView, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QColor, QBrush, QFont, QDesktopServices
from pathlib import Path
from typing import List, Optional, Dict, Any
import webbrowser

from ..shared.models import FileInfo, DuplicateGroup, ScanResult, ScanFilter
from ..shared.utils import format_size, format_datetime, highlight_text
from ..shared.constants import FILE_TYPE_FILTERS


class DirectorySelector(QWidget):
    directorySelected = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择要扫描的目录...")
        self.path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse)
        
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(self.browse_btn)
    
    def _browse(self):
        directory = QFileDialog.getExistingDirectory(self, "选择扫描目录")
        if directory:
            self.path_edit.setText(directory)
            self.directorySelected.emit(directory)
    
    def get_directory(self) -> str:
        return self.path_edit.text()
    
    def set_directory(self, path: str):
        self.path_edit.setText(path)


class FilterPanel(QWidget):
    filterChanged = pyqtSignal(object)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        type_group = QGroupBox("文件类型")
        type_layout = QHBoxLayout(type_group)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部文件", "all")
        for name, exts in FILE_TYPE_FILTERS.items():
            self.type_combo.addItem(name, exts)
        self.type_combo.currentIndexChanged.connect(self._on_filter_changed)
        
        type_layout.addWidget(self.type_combo)
        layout.addWidget(type_group)
        
        size_group = QGroupBox("文件大小")
        size_layout = QFormLayout(size_group)
        
        size_row = QHBoxLayout()
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 10 * 1024)
        self.min_size_spin.setValue(0)
        self.min_size_spin.setSuffix(" KB")
        self.min_size_spin.valueChanged.connect(self._on_filter_changed)
        
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 10 * 1024 * 1024)
        self.max_size_spin.setValue(0)
        self.max_size_spin.setSuffix(" KB")
        self.max_size_spin.valueChanged.connect(self._on_filter_changed)
        
        size_row.addWidget(QLabel("最小:"))
        size_row.addWidget(self.min_size_spin)
        size_row.addWidget(QLabel("最大:"))
        size_row.addWidget(self.max_size_spin)
        size_layout.addRow(size_row)
        
        layout.addWidget(size_group)
        
        date_group = QGroupBox("修改时间")
        date_layout = QVBoxLayout(date_group)
        
        self.date_combo = QComboBox()
        self.date_combo.addItem("不限", None)
        self.date_combo.addItem("今天", "today")
        self.date_combo.addItem("本周", "week")
        self.date_combo.addItem("本月", "month")
        self.date_combo.currentIndexChanged.connect(self._on_filter_changed)
        
        date_layout.addWidget(self.date_combo)
        layout.addWidget(date_group)
        
        options_group = QGroupBox("选项")
        options_layout = QVBoxLayout(options_group)
        
        self.skip_hidden_cb = QCheckBox("跳过隐藏文件")
        self.skip_hidden_cb.setChecked(True)
        self.skip_hidden_cb.stateChanged.connect(self._on_filter_changed)
        
        self.skip_system_cb = QCheckBox("跳过系统文件")
        self.skip_system_cb.setChecked(True)
        self.skip_system_cb.stateChanged.connect(self._on_filter_changed)
        
        options_layout.addWidget(self.skip_hidden_cb)
        options_layout.addWidget(self.skip_system_cb)
        layout.addWidget(options_group)
        
        layout.addStretch()
    
    def _on_filter_changed(self):
        filter_config = self.get_filter()
        self.filterChanged.emit(filter_config)
    
    def get_filter(self) -> ScanFilter:
        type_data = self.type_combo.currentData()
        
        extensions = []
        if type_data != "all" and type_data is not None:
            if isinstance(type_data, list):
                extensions = type_data
            elif isinstance(type_data, str):
                extensions = type_data.split(",") if type_data else []
        
        return ScanFilter(
            file_types=[self.type_combo.currentText()],
            min_size=self.min_size_spin.value() * 1024,
            max_size=self.max_size_spin.value() * 1024 if self.max_size_spin.value() > 0 else 0,
            date_filter=self.date_combo.currentData(),
            extensions=extensions,
            skip_hidden=self.skip_hidden_cb.isChecked(),
            skip_system=self.skip_system_cb.isChecked(),
        )
    
    def reset(self):
        self.type_combo.setCurrentIndex(0)
        self.min_size_spin.setValue(0)
        self.max_size_spin.setValue(0)
        self.date_combo.setCurrentIndex(0)
        self.skip_hidden_cb.setChecked(True)
        self.skip_system_cb.setChecked(True)


class DuplicateGroupList(QTreeWidget):
    groupSelected = pyqtSignal(object)
    fileSelected = pyqtSignal(object)
    openFileLocation = pyqtSignal(str)
    fileCheckStateChanged = pyqtSignal()  # 新增：文件勾选状态变化信号
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._groups: List[DuplicateGroup] = []
        self._init_ui()
    
    def _init_ui(self):
        self.setHeaderLabels(["文件路径", "大小", "修改时间", "状态"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.itemClicked.connect(self._on_item_clicked)
        self.itemChanged.connect(self._on_item_changed)  # 连接勾选状态变化信号
    
    def set_groups(self, groups: List[DuplicateGroup]):
        self._groups = groups
        self.clear()
        
        for group in groups:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, f"重复组 #{group.group_id + 1} ({len(group.files)} 个文件)")
            group_item.setText(1, format_size(group.wasted_space) + " 浪费")
            group_item.setData(0, Qt.ItemDataRole.UserRole, ("group", group.group_id))
            
            group_item.setExpanded(False)
            
            for file_info in group.files:
                file_item = QTreeWidgetItem(group_item)
                file_item.setText(0, file_info.path)
                file_item.setText(1, format_size(file_info.size))
                file_item.setText(2, format_datetime(file_info.mtime))
                file_item.setText(3, file_info.status)
                file_item.setData(0, Qt.ItemDataRole.UserRole, ("file", file_info))
                file_item.setCheckState(0, Qt.CheckState.Unchecked)
    
    def get_checked_files(self) -> List[FileInfo]:
        checked = []
        for i in range(self.topLevelItemCount()):
            group_item = self.topLevelItem(i)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item.checkState(0) == Qt.CheckState.Checked:
                    data = file_item.data(0, Qt.ItemDataRole.UserRole)
                    if data[0] == "file":
                        checked.append(data[1])
        return checked
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            if data[0] == "group":
                self.groupSelected.emit(self._groups[data[1]])
            elif data[0] == "file":
                self.fileSelected.emit(data[1])
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        # 当勾选状态变化时发出信号
        if column == 0:
            self.fileCheckStateChanged.emit()
    
    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data[0] != "file":
            return
        
        file_info: FileInfo = data[1]
        
        menu = QMenu(self)
        
        open_location_action = QAction("打开文件位置", self)
        open_location_action.triggered.connect(lambda: self.openFileLocation.emit(file_info.path))
        menu.addAction(open_location_action)
        
        menu.exec(self.viewport().mapToGlobal(pos))
    
    def search(self, keyword: str):
        keyword = keyword.lower().strip()
        if not keyword:
            for i in range(self.topLevelItemCount()):
                self.topLevelItem(i).setHidden(False)
            return
        
        for i in range(self.topLevelItemCount()):
            group_item = self.topLevelItem(i)
            has_match = False
            
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                path = file_item.text(0).lower()
                
                if keyword in path:
                    has_match = True
                    file_item.setHidden(False)
                    file_item.setText(0, highlight_text(file_item.text(0), keyword))
                else:
                    file_item.setHidden(True)
            
            group_item.setHidden(not has_match)


class FilePreviewPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        info_group = QGroupBox("文件信息")
        info_layout = QFormLayout(info_group)
        
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        self.size_label = QLabel("-")
        self.mtime_label = QLabel("-")
        self.hash_label = QLabel("-")
        self.hash_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label = QLabel("-")
        
        info_layout.addRow("路径:", self.path_label)
        info_layout.addRow("大小:", self.size_label)
        info_layout.addRow("修改时间:", self.mtime_label)
        info_layout.addRow("哈希:", self.hash_label)
        info_layout.addRow("状态:", self.status_label)
        
        layout.addWidget(info_group)
        layout.addStretch()
    
    def set_file_info(self, file_info: Optional[FileInfo]):
        if file_info is None:
            self.path_label.setText("-")
            self.size_label.setText("-")
            self.mtime_label.setText("-")
            self.hash_label.setText("-")
            self.status_label.setText("-")
            return
        
        self.path_label.setText(file_info.path)
        self.size_label.setText(format_size(file_info.size))
        self.mtime_label.setText(format_datetime(file_info.mtime))
        self.hash_label.setText(file_info.hash or "-")
        self.status_label.setText(file_info.status)


class QuarantinePanel(QWidget):
    fileRestored = pyqtSignal(str)
    fileDeleted = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("恢复选中")
        self.restore_btn.clicked.connect(self._on_restore)
        
        self.delete_btn = QPushButton("永久删除")
        self.delete_btn.clicked.connect(self._on_delete)
        
        self.clear_btn = QPushButton("清空隔离区")
        self.clear_btn.clicked.connect(self._on_clear)
        
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def set_files(self, files: List[tuple]):
        self.file_list.clear()
        for name, original_path in files:
            item = QListWidgetItem(f"{original_path}")
            item.setData(Qt.ItemDataRole.UserRole, (name, original_path))
            self.file_list.addItem(item)
    
    def _on_restore(self):
        item = self.file_list.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            self.fileRestored.emit(data[0])
    
    def _on_delete(self):
        item = self.file_list.currentItem()
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            self.fileDeleted.emit(data[0])
    
    def _on_clear(self):
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空隔离区吗？所有文件将被永久删除！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                data = item.data(Qt.ItemDataRole.UserRole)
                self.fileDeleted.emit(data[0])


class ExportDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("导出报告")
        self.setMinimumWidth(400)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItem("HTML 报告", "html")
        self.format_combo.addItem("CSV 表格", "csv")
        self.format_combo.addItem("JSON 数据", "json")
        
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("选择位置...")
        self.browse_btn.clicked.connect(self._browse)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(self.browse_btn)
        
        form_layout.addRow("格式:", self.format_combo)
        form_layout.addRow("保存位置:", path_layout)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
    
    def _browse(self):
        fmt = self.format_combo.currentData()
        ext = {"html": "html", "csv": "csv", "json": "json"}[fmt]
        
        path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", f"scan_report.{ext}",
            f"{fmt.upper()} Files (*.{ext})"
        )
        if path:
            self.path_edit.setText(path)
    
    def get_export_info(self) -> tuple:
        return self.format_combo.currentData(), self.path_edit.text()


class SearchBar(QWidget):
    searchChanged = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索文件名或路径...")
        self.search_edit.textChanged.connect(self._on_search_changed)
        
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self._clear)
        
        layout.addWidget(self.search_edit, 1)
        layout.addWidget(self.clear_btn)
    
    def _on_search_changed(self, text: str):
        self.searchChanged.emit(text)
    
    def _clear(self):
        self.search_edit.clear()
