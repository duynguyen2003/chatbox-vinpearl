#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
set -u

PY=""

# 1) Ưu tiên venv của chính dự án.
#
# submit_log.py và log_hook.py nạp .env bằng python-dotenv, nhưng bọc trong
# `try: import dotenv / except ImportError: pass`. Chạy bằng Python KHÔNG có
# dotenv thì .env bị bỏ qua trong im lặng, AI_LOG_SERVER thành rỗng, và
# submit_log báo "AI_LOG_SERVER not set — skipping submission" — log không bao
# giờ được gửi lên dù mọi thứ khác đều đúng.
#
# venv của dự án cài từ requirements.txt nên chắc chắn có python-dotenv.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for cand in "$REPO_ROOT/.venv/Scripts/python.exe" "$REPO_ROOT/.venv/bin/python"; do
  if [ -x "$cand" ]; then
    PY="$cand"
    break
  fi
done

# 2) Không có venv thì mới dò Python hệ thống.
# Đường dẫn dưới đây là của máy tác giả gốc; máy khác sẽ không có nên tự bỏ qua.
WIN_PY="/c/Users/Admin/AppData/Local/Programs/Python/Python311/python.exe"

if [ -n "$PY" ]; then
  :
elif [ -x "$WIN_PY" ]; then
  PY="$WIN_PY"
elif command -v python3 >/dev/null 2>&1; then
  CANDIDATE="$(command -v python3)"
  # Alias của Microsoft Store thiếu gói cài bằng pip -> phải loại ở CẢ python3
  # lẫn python, không chỉ riêng python như bản cũ.
  if [[ "$CANDIDATE" != *"/WindowsApps/"* ]]; then
    PY="$CANDIDATE"
  fi
fi

if [ -z "$PY" ] && command -v python >/dev/null 2>&1; then
  CANDIDATE="$(command -v python)"
  if [[ "$CANDIDATE" != *"/WindowsApps/"* ]]; then
    PY="$CANDIDATE"
  fi
fi

# Nếu vẫn chưa tìm thấy, dò các vị trí Python phổ biến
if [ -z "$PY" ]; then
  shopt -s nullglob 2>/dev/null || true

  for cand in \
    /c/Users/*/AppData/Local/Programs/Python/Python311/python.exe \
    /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
    "/c/Program Files/Python"*/python.exe \
    "/c/Program Files (x86)/Python"*/python.exe \
    /c/Python*/python.exe; do

    if [ -x "$cand" ]; then
      PY="$cand"
      break
    fi
  done

  shopt -u nullglob 2>/dev/null || true
fi

if [ -z "$PY" ]; then
  echo "[ai-log] Python not found." >&2
  exit 0
fi

exec "$PY" "$@"