"""Các script chạy bằng dòng lệnh (``python -m scripts.<ten>``).

Console mặc định trên máy Windows này dùng bảng mã cp1252, nên bất kỳ lệnh
``print`` nào có tiếng Việt cũng làm script chết với UnicodeEncodeError — kể cả
khi bản thân việc xử lý dữ liệu đã hoàn toàn đúng.

Đặt ở ``__init__.py`` để mọi script trong package tự động được sửa, khỏi phải
lặp lại ở từng file.
"""

from __future__ import annotations

import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
