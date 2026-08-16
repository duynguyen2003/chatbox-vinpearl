"""Chạy bộ test case hội thoại qua API /chat rồi điền kết quả vào chính file CSV.

    python -m scripts.run_test_cases                    # chạy đủ 70 ca
    python -m scripts.run_test_cases --limit 3          # chạy thử 3 ca
    python -m scripts.run_test_cases --only memory      # chỉ ca có test_id chứa 'memory'
    python -m scripts.run_test_cases --resume           # bỏ qua ca đã có kết quả

Ba cột được điền: assistant_answer, response_time_ms, status.

Ca nhiều lượt (cột user_message có dấu ' | ') chạy trong CÙNG một session_id để
kiểm tra trí nhớ hội thoại. Câu trả lời và thời gian của từng lượt nối bằng ' || ',
khớp đúng định dạng mà cột reference_hint đang dùng.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "tests" / "test_case" / "test_case_vi_cuong.csv"
DETAIL_PATH = CSV_PATH.with_name(CSV_PATH.stem + "_detail.jsonl")

TURN_SEP = " | "     # ngăn các lượt hỏi trong user_message
CELL_SEP = " || "    # ngăn kết quả từng lượt trong ô kết quả

# File có BOM. Đọc bằng 'utf-8' thường thì tên cột đầu thành '﻿test_id'
# và row['test_id'] ném KeyError. Ghi lại cũng giữ BOM để Excel mở tiếng Việt đúng.
ENCODING = "utf-8-sig"


# --------------------------------------------------------------------------
# Chấm điểm bằng "dữ kiện neo"
# --------------------------------------------------------------------------

# reference_hint là đoạn văn tham chiếu, không phải đáp án khớp từng ký tự, nên
# không so chuỗi được. Chấm theo hai tầng:
#
#   Tầng 1 — MỐC CỨNG: tiền, ngày, phần trăm, mã, số điện thoại, URL. Tín hiệu
#            mạnh nhất, nhưng chỉ khoảng 1/3 số hint có.
#   Tầng 2 — TỪ KHOÁ HIẾM: với hint không có mốc cứng, lấy những từ chỉ xuất
#            hiện ở ít hint (tần suất tài liệu thấp) rồi đo độ phủ. Cách này tự
#            học từ chính bộ dữ liệu nên không phải viết tay danh sách từ dừng —
#            "khách hàng", "dịch vụ", "Vinpearl" có mặt khắp nơi nên tự bị loại,
#            còn "cáp treo", "Hòn Tre", "voucher" thì giữ lại.
ANCHOR = re.compile(
    r"""
      https?://\S+                                 # https://www.vinpearl.com/
    | \d{1,3}(?:[.,]\d{3})+                        # 1.175.000 · 810.000
    | \b\d{1,2}/\d{1,2}/\d{4}\b                    # 31/12/2026
    | \b\d{1,3}\s*%                                # 30%
    | \b\d{1,2}:\d{2}\b                            # 09:00
    | \b\d{9,11}\b                                 # 1900232389
    | \b[A-Z][A-Z0-9_]{3,}\b                        # HAPPY10 · VP_PC04 · MEMBER3
    | \b\d+\s*(?:kg|cm|ha|lỗ|giờ|phút|triệu|đêm|tuổi)\b
    """,
    re.VERBOSE,
)

# Xuất hiện ở mọi câu trả lời nên không phân biệt được đúng/sai.
ANCHOR_STOPWORDS = {"VINPEARL", "VINWONDERS", "VNĐ", "VND", "USD", "FAQ"}

WORD = re.compile(r"[0-9A-Za-zÀ-ỹ]{4,}")

# Từ có mặt ở hơn ngần này phần hint thì coi là từ chung, bỏ.
COMMON_WORD_RATIO = 0.20

_rare_words: set[str] = set()


def build_vocabulary(hints: list[str]) -> None:
    """Học xem từ nào là từ chung, từ nào đủ hiếm để làm mốc đối chiếu."""
    global _rare_words
    df: dict[str, int] = {}
    for hint in hints:
        for w in {m.lower() for m in WORD.findall(hint)}:
            df[w] = df.get(w, 0) + 1
    ceiling = max(2, int(len(hints) * COMMON_WORD_RATIO))
    _rare_words = {w for w, n in df.items() if n <= ceiling}


def digit_norm(text: str) -> str:
    """1.175.000 và 1,175,000 phải so được với nhau."""
    return re.sub(r"(?<=\d)[.,](?=\d)", "", text)


def anchors_of(hint: str) -> list[str]:
    found = []
    for raw in ANCHOR.findall(hint):
        token = raw.strip().rstrip(".,;")
        if token.upper() in ANCHOR_STOPWORDS:
            continue
        if token not in found:
            found.append(token)
    return found


def keywords_of(hint: str) -> list[str]:
    seen = []
    for m in WORD.findall(hint):
        w = m.lower()
        if w in _rare_words and w not in seen:
            seen.append(w)
    return seen


def grade(hint: str, answer: str) -> tuple[str, list[str], list[str]]:
    """-> (status, mốc tìm thấy, mốc thiếu)"""
    haystack = digit_norm(answer).upper()
    flat = haystack.replace(" ", "")

    keys = anchors_of(hint)
    if keys:
        hit = [k for k in keys if digit_norm(k).upper().replace(" ", "") in flat]
        threshold = 0.6
    else:
        keys = keywords_of(hint)
        if not keys:
            return "REVIEW", [], []
        hit = [k for k in keys if k.upper() in haystack]
        # Từ khoá là tín hiệu yếu hơn mốc cứng nên hạ ngưỡng xuống.
        threshold = 0.45

    miss = [k for k in keys if k not in hit]
    ratio = len(hit) / len(keys)
    if ratio >= threshold:
        return "PASS", hit, miss
    if ratio > 0:
        return "PARTIAL", hit, miss
    return "FAIL", hit, miss


# --------------------------------------------------------------------------
# Gọi API
# --------------------------------------------------------------------------


def ask(client: httpx.Client, base: str, message: str,
        session_id: str | None) -> tuple[dict[str, Any], int]:
    """Gọi POST /chat, trả về (payload, mili giây). Thử lại khi bị giới hạn tốc độ."""
    body: dict[str, Any] = {"message": message}
    if session_id:
        body["session_id"] = session_id

    delay = 5.0
    last: Exception | None = None
    for attempt in range(1, 5):
        started = time.perf_counter()
        try:
            r = client.post(f"{base}/chat", json=body)
            elapsed = int((time.perf_counter() - started) * 1000)
            if r.status_code == 200:
                return r.json(), elapsed
            # 429 = quá giới hạn tốc độ, 5xx = lỗi tạm — chờ rồi thử lại.
            if r.status_code == 429 or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
                if attempt < 4:
                    time.sleep(delay)
                    delay *= 2
                    continue
            return {"answer": "", "error": f"HTTP {r.status_code}: {r.text[:300]}"}, elapsed
        except Exception as exc:  # noqa: BLE001 - ghi lai roi thu lai
            last = exc
            if attempt < 4:
                time.sleep(delay)
                delay *= 2
    return {"answer": "", "error": f"{type(last).__name__}: {last}"}, 0


def run_case(client: httpx.Client, base: str, row: dict[str, str]) -> dict[str, Any]:
    turns = [t.strip() for t in row["user_message"].split(TURN_SEP) if t.strip()]
    answers: list[str] = []
    times: list[int] = []
    detail: list[dict[str, Any]] = []
    session_id: str | None = None
    error: str | None = None

    for index, turn in enumerate(turns, start=1):
        payload, ms = ask(client, base, turn, session_id)
        session_id = payload.get("session_id") or session_id
        answer = (payload.get("answer") or "").strip()
        answers.append(answer)
        times.append(ms)
        if payload.get("error") and not error:
            error = str(payload["error"])
        detail.append({
            "turn": index,
            "question": turn,
            "answer": answer,
            "ms": ms,
            "route": payload.get("route"),
            "language": payload.get("language"),
            "sources": [s.get("source_file") for s in (payload.get("sources") or [])],
            "error": payload.get("error"),
        })

    answer_cell = CELL_SEP.join(answers)
    time_cell = CELL_SEP.join(str(t) for t in times)

    if error:
        status, hit, miss = "ERROR", [], []
    else:
        status, hit, miss = grade(row["reference_hint"], answer_cell)

    return {
        "test_id": row["test_id"],
        "type": row["type"],
        "answer_cell": answer_cell,
        "time_cell": time_cell,
        "status": status,
        "session_id": session_id,
        "turns": detail,
        "anchors_hit": hit,
        "anchors_miss": miss,
        "error": error,
    }


# --------------------------------------------------------------------------


def summarise(results: list[dict[str, Any]]) -> None:
    order = ["PASS", "PARTIAL", "FAIL", "REVIEW", "ERROR"]
    total = {s: 0 for s in order}
    by_type: dict[str, dict[str, int]] = {}

    for r in results:
        total[r["status"]] = total.get(r["status"], 0) + 1
        bucket = by_type.setdefault(r["type"], {s: 0 for s in order})
        bucket[r["status"]] += 1

    print(f"\n{'=' * 72}")
    print(f"TỔNG {len(results)} ca   " + "   ".join(f"{s} {total[s]}" for s in order))
    print("=" * 72)

    width = max(len(t) for t in by_type) if by_type else 10
    for name in sorted(by_type):
        b = by_type[name]
        print(f"  {name:<{width}}  " + "  ".join(f"{s} {b[s]:>2}" for s in order if b[s]))

    every_ms = [int(x) for r in results for x in r["time_cell"].split(CELL_SEP) if x.isdigit()]
    if every_ms:
        every_ms.sort()
        p = lambda q: every_ms[min(len(every_ms) - 1, int(len(every_ms) * q))]  # noqa: E731
        print(f"\n  thời gian mỗi lượt ({len(every_ms)} lượt):"
              f"  trung vị {p(0.5)}ms   p95 {p(0.95)}ms   max {every_ms[-1]}ms"
              f"   tổng {sum(every_ms) / 1000:.0f}s")
        print(f"  trung bình {statistics.mean(every_ms):.0f}ms")

    bad = [r for r in results if r["status"] in ("FAIL", "ERROR", "PARTIAL")]
    if bad:
        print(f"\n  CẦN XEM LẠI ({len(bad)}):")
        for r in bad:
            note = r["error"] or ("thiếu mốc: " + ", ".join(r["anchors_miss"][:4]))
            print(f"    [{r['status']:<7}] {r['test_id']:<26} {note[:70]}")

    review = [r for r in results if r["status"] == "REVIEW"]
    if review:
        print(f"\n  ĐỌC TAY ({len(review)}) — hint không có mốc cứng để máy bám:")
        for r in review:
            print(f"    {r['test_id']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8000/api/v1")
    ap.add_argument("--csv", type=Path, default=CSV_PATH)
    ap.add_argument("--limit", type=int, help="chỉ chạy N ca đầu")
    ap.add_argument("--only", help="chỉ chạy ca có test_id chứa chuỗi này")
    ap.add_argument("--sleep", type=float, default=0.5, help="nghỉ giữa các ca (giây)")
    ap.add_argument("--timeout", type=float, default=200.0)
    ap.add_argument("--resume", action="store_true", help="bỏ qua ca đã có assistant_answer")
    args = ap.parse_args()

    with args.csv.open(encoding=ENCODING, newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = list(reader)

    build_vocabulary([r["reference_hint"] for r in rows])

    todo = rows
    if args.only:
        todo = [r for r in todo if args.only in r["test_id"]]
    if args.resume:
        # Bỏ qua ca đã chạy XONG. Ca ERROR có ô trả lời rỗng nên vẫn được
        # chạy lại — đó là điều ta muốn khi lần trước bị hết hạn mức.
        todo = [r for r in todo
                if (r.get("status") or "").strip() in ("", "ERROR")
                or not (r.get("assistant_answer") or "").strip()]
    if args.limit:
        todo = todo[: args.limit]

    if not todo:
        print("Không có ca nào để chạy.")
        return 0

    turns = sum(len(r["user_message"].split(TURN_SEP)) for r in todo)
    print(f"Chạy {len(todo)}/{len(rows)} ca — {turns} lượt gọi — {args.url}\n")

    by_id = {r["test_id"]: r for r in rows}
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=args.timeout) as client, \
            DETAIL_PATH.open("a", encoding="utf-8") as detail_fh:
        for index, row in enumerate(todo, start=1):
            n_turn = len(row["user_message"].split(TURN_SEP))
            label = f"[{index:>2}/{len(todo)}] {row['test_id']:<26}"
            print(f"{label} {n_turn} lượt ... ", end="", flush=True)

            result = run_case(client, args.url, row)
            results.append(result)

            target = by_id[row["test_id"]]
            target["assistant_answer"] = result["answer_cell"]
            target["response_time_ms"] = result["time_cell"]
            target["status"] = result["status"]

            detail_fh.write(json.dumps(
                {"ran_at": time.strftime("%Y-%m-%d %H:%M:%S"), **result},
                ensure_ascii=False) + "\n")
            detail_fh.flush()

            # Ghi lại CSV sau MỖI ca: 93 lượt gọi mất hàng chục phút, đứt giữa
            # chừng mà mất hết thì phải chạy lại từ đầu.
            with args.csv.open("w", encoding=ENCODING, newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)

            total_ms = sum(int(x) for x in result["time_cell"].split(CELL_SEP) if x.isdigit())
            print(f"{result['status']:<7} {total_ms:>6}ms")

            if args.sleep and index < len(todo):
                time.sleep(args.sleep)

    summarise(results)
    print(f"\nĐã ghi: {args.csv}")
    print(f"Chi tiết từng lượt: {DETAIL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
