from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMessageBox, QProgressBar, QTabWidget,
    QLabel, QMenu, QMenuBar, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent

from .controllers import AppController
from .widgets import (
    DirectorySelector, FilterPanel, DuplicateGroupList,
    FilePreviewPanel, QuarantinePanel, ExportDialog, SearchBar
)
from ..shared.models import ScanResult, FileInfo, DuplicateGroup
from ..shared.utils import format_size


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self._controller = AppController(self)
        self._is_scanning = False
        
        self._init_ui()
        self._connect_signals()
        self._restore_state()
    
    def _init_ui(self):
        self.setWindowTitle("文件去重整理器")
        self.setMinimumSize(1000, 700)
        
        self._create_menus()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
    
    def _create_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        self.scan_action = QAction("扫描目录(&S)", self)
        self.scan_action.setShortcut(QKeySequence.StandardKey.Open)
        self.scan_action.triggered.connect(self._on_scan)
        file_menu.addAction(self.scan_action)
        
        self.cancel_action = QAction("取消扫描(&C)", self)
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self._on_cancel_scan)
        file_menu.addAction(self.cancel_action)
        
        file_menu.addSeparator()
        
        self.export_action = QAction("导出报告(&E)", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self._on_export)
        self.export_action.setEnabled(False)
        file_menu.addAction(self.export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        action_menu = menubar.addMenu("操作(&A)")
        
        self.move_action = QAction("移动到隔离区(&M)", self)
        self.move_action.triggered.connect(self._on_move_to_quarantine)
        self.move_action.setEnabled(False)
        action_menu.addAction(self.move_action)
        
        self.delete_action = QAction("永久删除(&D)", self)
        self.delete_action.triggered.connect(self._on_delete_files)
        self.delete_action.setEnabled(False)
        action_menu.addAction(self.delete_action)
        
        action_menu.addSeparator()
        
        self.refresh_quarantine_action = QAction("刷新隔离区(&R)", self)
        self.refresh_quarantine_action.triggered.connect(self._refresh_quarantine)
        action_menu.addAction(self.refresh_quarantine_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        self.dir_selector = DirectorySelector()
        toolbar.addWidget(self.dir_selector)
        
        toolbar.addSeparator()
        
        self.scan_btn = QAction("开始扫描", self)
        self.scan_btn.triggered.connect(self._on_scan)
        toolbar.addAction(self.scan_btn)
        
        self.cancel_btn = QAction("取消", self)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.triggered.connect(self._on_cancel_scan)
        toolbar.addAction(self.cancel_btn)
    
    def _create_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.search_bar = SearchBar()
        main_layout.addWidget(self.search_bar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.filter_panel = FilterPanel()
        splitter.addWidget(self.filter_panel)
        
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.tab_widget = QTabWidget()
        
        self.group_list = DuplicateGroupList()
        self.tab_widget.addTab(self.group_list, "重复文件")
        
        self.quarantine_panel = QuarantinePanel()
        self.tab_widget.addTab(self.quarantine_panel, "隔离区")
        
        right_splitter.addWidget(self.tab_widget)
        
        self.preview_panel = FilePreviewPanel()
        right_splitter.addWidget(self.preview_panel)
        
        right_splitter.setSizes([500, 150])
        
        splitter.addWidget(right_splitter)
        
        splitter.setSizes([200, 800])
        
        main_layout.addWidget(splitter, 1)
        
        self._splitter = splitter
    
    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        self.stats_label = QLabel()
        self.status_bar.addPermanentWidget(self.stats_label)
    
    def _connect_signals(self):
        self.dir_selector.directorySelected.connect(self._on_directory_selected)
        
        self._controller.scanStarted.connect(self._on_scan_started)
        self._controller.scanProgress.connect(self._on_scan_progress)
        self._controller.hashProgress.connect(self._on_hash_progress)
        self._controller.scanFinished.connect(self._on_scan_finished)
        self._controller.scanError.connect(self._on_scan_error)
        self._controller.operationStarted.connect(self._on_operation_started)
        self._controller.operationProgress.connect(self._on_operation_progress)
        self._controller.operationFinished.connect(self._on_operation_finished)
        
        self.group_list.fileSelected.connect(self.preview_panel.set_file_info)
        self.group_list.openFileLocation.connect(self._controller.open_file_location)
        self.group_list.checkedFilesChanged.connect(self._update_ui_state)
        
        self.search_bar.searchChanged.connect(self.group_list.search)
        
        self.quarantine_panel.fileRestored.connect(self._on_restore_file)
        self.quarantine_panel.fileDeleted.connect(self._on_delete_from_quarantine)
        self.quarantine_panel.clearAllRequested.connect(self._on_clear_quarantine)
    
    def _restore_state(self):
        geometry = self._controller.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        state = self._controller.get_splitter_state()
        if state:
            self._splitter.restoreState(state)
        
        recent = self._controller.get_recent_directories()
        if recent:
            self.dir_selector.set_directory(recent[0])
    
    def closeEvent(self, event: QCloseEvent):
        self._controller.save_window_geometry(self.saveGeometry())
        self._controller.save_splitter_state(self._splitter.saveState())
        self._controller.sync_settings()
        event.accept()
    
    def _on_directory_selected(self, directory: str):
        pass
    
    def _on_scan(self):
        directory = self.dir_selector.get_directory()
        if not directory:
            QMessageBox.warning(self, "警告", "请先选择要扫描的目录")
            return
        
        filter_config = self.filter_panel.get_filter()
        self._controller.start_scan(directory, filter_config)
    
    def _on_cancel_scan(self):
        self._controller.cancel_scan()
        self._is_scanning = False
        self._update_ui_state()
    
    def _on_scan_started(self):
        self._is_scanning = True
        self._update_ui_state()
        self.status_label.setText("正在扫描目录...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def _on_scan_progress(self, current: int, total: int, path: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"扫描中: {path}")
    
    def _on_hash_progress(self, current: int, total: int, path: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"计算哈希: {Path(path).name}")
    
    def _on_scan_finished(self, result: Optional[ScanResult]):
        self._is_scanning = False
        self._update_ui_state()
        
        if result:
            self.group_list.set_groups(result.duplicate_groups)
            self.stats_label.setText(
                f"总文件: {result.total_files} | "
                f"重复组: {len(result.duplicate_groups)} | "
                f"浪费空间: {format_size(result.total_wasted)}"
            )
            self.status_label.setText("扫描完成")
            self.export_action.setEnabled(True)
        else:
            self.status_label.setText("扫描已取消")
        
        self.progress_bar.setVisible(False)
    
    def _on_scan_error(self, error: str):
        self._is_scanning = False
        self._update_ui_state()
        QMessageBox.critical(self, "错误", error)
        self.status_label.setText("扫描出错")
        self.progress_bar.setVisible(False)
    
    def _on_operation_started(self, operation: str):
        self.status_label.setText(f"正在{operation}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
    
    def _on_operation_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def _on_operation_finished(self, operation: str, success: int, fail: int):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"{operation}完成: {success} 成功, {fail} 失败")
        
        if self._current_result:
            self.group_list.set_groups(self._current_result.duplicate_groups)
        
        self.preview_panel.clear()
        self._refresh_quarantine()
    
    @property
    def _current_result(self):
        return self._controller._current_result
    
    def _update_ui_state(self):
        scanning = self._is_scanning
        
        self.scan_action.setEnabled(not scanning)
        self.scan_btn.setEnabled(not scanning)
        self.cancel_action.setEnabled(scanning)
        self.cancel_btn.setEnabled(scanning)
        self.filter_panel.setEnabled(not scanning)
        self.dir_selector.setEnabled(not scanning)
        
        has_selection = len(self.group_list.get_checked_files()) > 0
        self.move_action.setEnabled(has_selection and not scanning)
        self.delete_action.setEnabled(has_selection and not scanning)
    
    def _on_move_to_quarantine(self):
        files = self.group_list.get_checked_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先勾选要处理的文件")
            return
        
        reply = QMessageBox.question(
            self, "确认",
            f"确定要将选中的 {len(files)} 个文件移动到隔离区吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.move_to_quarantine(files)
    
    def _on_delete_files(self):
        files = self.group_list.get_checked_files()
        if not files:
            QMessageBox.warning(self, "警告", "请先勾选要处理的文件")
            return
        
        reply = QMessageBox.warning(
            self, "确认删除",
            f"确定要永久删除选中的 {len(files)} 个文件吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._controller.delete_files(files, use_trash=False)
    
    def _on_export(self):
        dialog = ExportDialog(self)
        if dialog.exec():
            format_type, path = dialog.get_export_info()
            if path:
                if self._controller.export_report(format_type, path):
                    QMessageBox.information(self, "成功", f"报告已导出到:\n{path}")
                else:
                    QMessageBox.critical(self, "错误", "导出失败")
    
    def _refresh_quarantine(self):
        files = self._controller.get_quarantined_files()
        self.quarantine_panel.set_files(files)
    
    def _on_restore_file(self, quarantined_name: str):
        success, message = self._controller.restore_file(quarantined_name)
        if success:
            self.status_label.setText(f"文件已恢复: {message}")
            self._refresh_quarantine()
        else:
            QMessageBox.critical(self, "恢复失败", message)
    
    def _on_delete_from_quarantine(self, quarantined_name: str):
        success, message = self._controller.delete_from_quarantine(quarantined_name)
        if success:
            self._refresh_quarantine()
        else:
            QMessageBox.critical(self, "删除失败", message)
    
    def _on_clear_quarantine(self):
        success, message = self._controller.clear_quarantine()
        if success:
            self.status_label.setText(message)
            self._refresh_quarantine()
        else:
            QMessageBox.critical(self, "清空失败", message)
    
    def _on_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>文件去重整理器</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>扫描、识别和管理重复文件</p>"
            "<p>功能特性:</p>"
            "<ul>"
            "<li>递归扫描目录，按哈希分组重复文件</li>"
            "<li>支持按类型、大小、修改时间过滤</li>"
            "<li>批量移动到隔离区或永久删除</li>"
            "<li>搜索文件名与路径，关键词高亮</li>"
            "<li>导出扫描报告为 HTML 或 CSV</li>"
            "</ul>"
        )
