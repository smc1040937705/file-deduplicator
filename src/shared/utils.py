from datetime import datetime
from typing import List, Tuple


def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            if unit == 'B':
                return f"{size} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def format_datetime(dt: datetime) -> str:
    if dt is None:
        return ""
    if isinstance(dt, (int, float)):
        dt = datetime.fromtimestamp(dt)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp(timestamp: float) -> str:
    if timestamp is None:
        return ""
    return format_datetime(datetime.fromtimestamp(timestamp))


def highlight_text(text: str, keywords: str, 
                   prefix: str = '<span style="background-color: #ffff00;">',
                   suffix: str = '</span>',
                   case_sensitive: bool = True) -> str:
    if not keywords or not text:
        return text
    
    if isinstance(keywords, list):
        keyword_list = keywords
    else:
        keyword_list = keywords.split()
    
    result = text
    for keyword in keyword_list:
        if not keyword:
            continue
        if not case_sensitive:
            lower_text = result.lower()
            lower_keyword = keyword.lower()
            start = 0
            parts = []
            last_end = 0
            
            while True:
                pos = lower_text.find(lower_keyword, start)
                if pos == -1:
                    parts.append(result[last_end:])
                    break
                parts.append(result[last_end:pos])
                parts.append(prefix)
                parts.append(result[pos:pos + len(keyword)])
                parts.append(suffix)
                last_end = pos + len(keyword)
                start = last_end
            
            result = ''.join(parts)
        else:
            start = 0
            parts = []
            last_end = 0
            
            while True:
                pos = result.find(keyword, start)
                if pos == -1:
                    parts.append(result[last_end:])
                    break
                parts.append(result[last_end:pos])
                parts.append(prefix)
                parts.append(result[pos:pos + len(keyword)])
                parts.append(suffix)
                last_end = pos + len(keyword)
                start = last_end
            
            result = ''.join(parts)
    
    return result


def get_file_extension(filename: str) -> str:
    if '.' not in filename:
        return ""
    return filename.rsplit('.', 1)[-1].lower()


def get_file_type_category(extension: str) -> str:
    from .constants import FILE_TYPE_FILTERS
    
    ext_lower = extension.lower() if extension else ""
    if not ext_lower.startswith('.'):
        ext_lower = '.' + ext_lower
    
    for category, extensions in FILE_TYPE_FILTERS.items():
        if category == "all":
            continue
        if isinstance(extensions, list) and ext_lower in extensions:
            return category
    
    return "other"


def parse_size_filter(size_str: str) -> Tuple[int, int]:
    from .constants import SIZE_FILTERS
    
    for name, min_size, max_size in SIZE_FILTERS:
        if name == size_str:
            return (min_size, max_size)
    return (0, float('inf'))


def escape_html(text: str) -> str:
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))
