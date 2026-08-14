"""Chay test_case_vi_an.csv: gui cau hoi toi backend, dien cau tra loi vao CSV.

Cach dung (anh host backend truoc):
    python tests/test_case/utils/run_test_case_vi_an.py
    python tests/test_case/utils/run_test_case_vi_an.py --resume
    python tests/test_case/utils/run_test_case_vi_an.py --limit 3
    python tests/test_case/utils/run_test_case_vi_an.py --only faq-004,memory-hoi-an
    python tests/test_case/utils/run_test_case_vi_an.py --api-url http://127.0.0.1:8000/api/v1/chat

Quy uoc:
    - Khong Memory: 1 cau hoi, 1 session moi (giong F5 trang).
    - Memory: nhieu luot cung session, dap an ngan cach bang " || ".
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "test_case_vi_an.csv"
API_URL = "http://127.0.0.1:8000/api/v1/chat"
TIMEOUT = 180.0
SLEEP_AFTER_TURN = 1.0
SLEEP_AFTER_F5 = 0.4
DONE_STATUS = {"pass", "fail"}


def _is_memory(row: dict[str, str]) -> bool:
    kind = (row.get("type") or "").strip().lower()
    test_id = (row.get("test_id") or "").strip().lower()
    return kind == "memory" or test_id.startswith("memory-")


def _split_turns(user_message: str) -> list[str]:
    parts = [part.strip() for part in user_message.split(" | ")]
    return [part for part in parts if part]


def _new_session(test_id: str) -> str:
    return f"an-{test_id}-{uuid4().hex[:8]}"


def _chat(client: httpx.Client, api_url: str, message: str, session_id: str) -> tuple[str, int, str]:
    started = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = client.post(
                api_url,
                json={"message": message, "session_id": session_id},
                timeout=TIMEOUT,
            )
            if response.status_code in {500, 503}:
                detail = ""
                try:
                    detail = str(response.json().get("detail") or "")
                except Exception:  # noqa: BLE001
                    detail = response.text
                print(
                    f"    {response.status_code} {detail} — retry {attempt}/3",
                    flush=True,
                )
                time.sleep(8 * attempt)
                last_error = httpx.HTTPStatusError(
                    str(response.status_code),
                    request=response.request,
                    response=response,
                )
                continue
            response.raise_for_status()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            answer = (response.json().get("answer") or "").strip()
            if not answer:
                return "", elapsed_ms, "fail"
            return answer, elapsed_ms, "pass"
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response is not None and exc.response.status_code in {500, 503}:
                time.sleep(8 * attempt)
                continue
            raise
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    raise last_error or RuntimeError("chat failed after retries")


def _run_row(client: httpx.Client, api_url: str, row: dict[str, str]) -> dict[str, str]:
    raw_message = row.get("user_message") or ""
    memory = _is_memory(row)
    turns = _split_turns(raw_message) if memory else [raw_message.strip()]
    turns = [turn for turn in turns if turn]

    session_id = _new_session(row.get("test_id") or "case")
    answers: list[str] = []
    total_ms = 0
    status = "pass"

    for index, turn in enumerate(turns):
        try:
            answer, elapsed_ms, turn_status = _chat(client, api_url, turn, session_id)
            total_ms += elapsed_ms
            if turn_status == "fail":
                status = "fail"
            answers.append(answer or f"[empty answer after {elapsed_ms}ms]")
        except Exception as exc:  # noqa: BLE001
            status = "fail"
            answers.append(f"[error: {exc}]")
            break
        if memory and index < len(turns) - 1:
            time.sleep(SLEEP_AFTER_TURN)

    # Cau khong Memory: xong 1 cau thi F5 — session moi, khong mang ngu canh sang case sau.
    if not memory:
        time.sleep(SLEEP_AFTER_F5)
        print(f"    F5 session={session_id} -> new chat", flush=True)

    row = dict(row)
    row["assistant_answer"] = " || ".join(answers) if memory else (answers[0] if answers else "")
    row["response_time_ms"] = str(total_ms)
    row["status"] = status
    return row


def _should_run(row: dict[str, str], only: set[str], force: bool, resume: bool) -> bool:
    tid = row.get("test_id") or ""
    if only and tid not in only:
        return False
    if force:
        return True
    if resume and (row.get("status") or "").strip().lower() in DONE_STATUS:
        return False
    if not resume and (row.get("assistant_answer") or "").strip():
        return False
    return True


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> Path:
    try:
        target = path
        with target.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return target
    except PermissionError:
        fallback = path.with_name(f"{path.stem}_results.csv")
        with fallback.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return fallback


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chay test_case_vi_an.csv: 1 cau + F5; Memory giu session va noi ||"
    )
    parser.add_argument("csv_path", nargs="?", default=str(DEFAULT_CSV))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--api-url", default=API_URL)
    args = parser.parse_args()

    csv_path = Path(args.csv_path).resolve()
    if not csv_path.exists():
        print(f"Khong thay CSV: {csv_path}", file=sys.stderr)
        return 1

    only = {part.strip() for part in args.only.split(",") if part.strip()}
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig", newline="")))
    if not rows:
        print("CSV trong.")
        return 0
    fields = list(rows[0].keys())

    health_url = args.api_url.replace("/api/v1/chat", "/health")
    try:
        health = httpx.get(health_url, timeout=5.0)
        health.raise_for_status()
    except Exception as exc:
        print(
            f"Backend chua san sang tai {health_url}: {exc}\n"
            "Hay host backend truoc, vi du:\n"
            "  python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000",
            file=sys.stderr,
        )
        return 1

    ran = 0
    out_path = csv_path
    with httpx.Client() as client:
        for idx, row in enumerate(rows):
            if not _should_run(row, only, args.force, args.resume):
                continue
            if args.limit and ran >= args.limit:
                break

            kind = "Memory" if _is_memory(row) else "1-cau + F5"
            print(f"[{ran + 1}] {row['test_id']} ({kind}) ...", flush=True)
            rows[idx] = _run_row(client, args.api_url, row)
            preview = (rows[idx]["assistant_answer"] or "").replace("\n", " ")[:160]
            print(
                f"    status={rows[idx]['status']} "
                f"time={rows[idx]['response_time_ms']}ms "
                f"answer={preview}",
                flush=True,
            )
            out_path = _write_csv(csv_path, fields, rows)
            ran += 1

    if ran == 0:
        print("Khong con case de chay.")
        return 0

    print(f"\nDa chay {ran} case. Ghi -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
