import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from io import StringIO

from ..shared.models import ScanResult, DuplicateGroup, FileInfo
from ..shared.utils import format_size, format_datetime, escape_html


class ReportExporter:
    @staticmethod
    def export_to_csv(result: ScanResult, output_path: str) -> bool:
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                writer.writerow([
                    "分组ID", "文件哈希", "文件路径", "文件大小(字节)", 
                    "文件大小", "修改时间", "是否重复", "状态"
                ])
                
                for group in result.duplicate_groups:
                    for file_info in group.files:
                        writer.writerow([
                            group.group_id,
                            group.hash,
                            file_info.path,
                            file_info.size,
                            format_size(file_info.size),
                            format_datetime(file_info.mtime),
                            "是" if file_info.is_duplicate else "否",
                            file_info.status,
                        ])
                
                writer.writerow([])
                writer.writerow(["统计信息"])
                writer.writerow(["扫描目录", result.directory])
                writer.writerow(["扫描时间", format_datetime(result.scan_time)])
                writer.writerow(["总文件数", result.total_files])
                writer.writerow(["重复组数", len(result.duplicate_groups)])
                writer.writerow(["浪费空间", format_size(result.total_wasted)])
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def export_to_html(result: ScanResult, output_path: str) -> bool:
        try:
            html = StringIO()
            
            html.write("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件去重扫描报告</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .summary {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary-item {
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }
        .summary-label {
            color: #666;
            font-size: 14px;
        }
        .summary-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .group {
            background: white;
            margin-bottom: 15px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .group-header {
            background: #4CAF50;
            color: white;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .group-header h3 {
            margin: 0;
        }
        .group-info {
            display: flex;
            gap: 20px;
        }
        .group-info span {
            background: rgba(255,255,255,0.2);
            padding: 5px 10px;
            border-radius: 4px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f9f9f9;
            font-weight: 600;
            color: #666;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .path {
            font-family: monospace;
            font-size: 13px;
            word-break: break-all;
        }
        .hash {
            font-family: monospace;
            font-size: 12px;
            color: #666;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>文件去重扫描报告</h1>
    
    <div class="summary">
        <div class="summary-item">
            <div class="summary-label">扫描目录</div>
            <div class="summary-value">""" + escape_html(result.directory) + """</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">扫描时间</div>
            <div class="summary-value">""" + format_datetime(result.scan_time) + """</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">总文件数</div>
            <div class="summary-value">""" + str(result.total_files) + """</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">重复组数</div>
            <div class="summary-value">""" + str(len(result.duplicate_groups)) + """</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">浪费空间</div>
            <div class="summary-value" style="color: #f44336;">""" + format_size(result.total_wasted) + """</div>
        </div>
    </div>
""")
            
            for group in result.duplicate_groups:
                html.write(f"""
    <div class="group">
        <div class="group-header">
            <h3>重复组 #{group.group_id + 1}</h3>
            <div class="group-info">
                <span>{len(group.files)} 个文件</span>
                <span>浪费: {format_size(group.wasted_space)}</span>
            </div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>文件路径</th>
                    <th>大小</th>
                    <th>修改时间</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
""")
                
                for file_info in group.files:
                    html.write(f"""
                <tr>
                    <td class="path">{escape_html(file_info.path)}</td>
                    <td>{format_size(file_info.size)}</td>
                    <td>{format_datetime(file_info.mtime)}</td>
                    <td>{file_info.status}</td>
                </tr>
""")
                
                html.write("""
            </tbody>
        </table>
    </div>
""")
            
            html.write(f"""
    <div class="footer">
        <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>由 FileDeduplicator 生成</p>
    </div>
</body>
</html>
""")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html.getvalue())
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def export_to_json(result: ScanResult, output_path: str) -> bool:
        try:
            data = {
                "directory": result.directory,
                "scan_time": result.scan_time,
                "total_files": result.total_files,
                "total_wasted": result.total_wasted,
                "duplicate_groups": [
                    {
                        "group_id": group.group_id,
                        "hash": group.hash,
                        "total_size": group.total_size,
                        "wasted_space": group.wasted_space,
                        "files": [
                            {
                                "path": f.path,
                                "size": f.size,
                                "mtime": f.mtime,
                                "is_duplicate": f.is_duplicate,
                                "status": f.status,
                            }
                            for f in group.files
                        ]
                    }
                    for group in result.duplicate_groups
                ]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False
