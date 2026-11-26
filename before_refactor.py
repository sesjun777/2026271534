from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _category_for(path: Path) -> str:
    """구조 개선 전: 분류 규칙이 함수 내부의 긴 조건문에 직접 결합되어 있다."""
    suffix = path.suffix.lower()

    if suffix in {".pdf", ".docx", ".txt", ".md"}:
        return "Documents"
    elif suffix in {".jpg", ".jpeg", ".png", ".gif"}:
        return "Images"
    elif suffix in {".csv", ".json", ".xlsx"}:
        return "Data"
    elif suffix in {".mp4", ".mov"}:
        return "Videos"
    elif suffix in {".zip", ".tar", ".gz"}:
        return "Archives"
    else:
        return "Others"


def _validate(source: Path, output: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"입력 폴더가 없습니다: {source}")
    if not source.is_dir():
        raise NotADirectoryError(f"입력 경로가 폴더가 아닙니다: {source}")
    if source.resolve() == output.resolve():
        raise ValueError("입력 폴더와 출력 폴더는 달라야 합니다.")


def preview_plan(source: str | Path, output: str | Path) -> list[dict[str, str]]:
    source = Path(source)
    output = Path(output)
    _validate(source, output)

    plan: list[dict[str, str]] = []
    for file in sorted(source.iterdir(), key=lambda p: p.name.lower()):
        if not file.is_file():
            continue

        category = _category_for(file)
        destination = output / category / file.name
        plan.append(
            {
                "source": str(file),
                "destination": str(destination),
                "category": category,
            }
        )
    return plan


def organize_files(
    source: str | Path,
    output: str | Path,
    log_path: str | Path | None = None,
) -> list[dict[str, str]]:
    source = Path(source)
    output = Path(output)
    plan = preview_plan(source, output)

    if log_path is None:
        log_path = output / "organizer_log.jsonl"
    else:
        log_path = Path(log_path)

    results: list[dict[str, str]] = []
    for item in plan:
        src = Path(item["source"])
        dst = Path(item["destination"])
        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            raise FileExistsError(f"대상 파일이 이미 존재합니다: {dst}")

        shutil.copy2(src, dst)
        record = {
            **item,
            "status": "copied",
            "time_utc": datetime.now(timezone.utc).isoformat(),
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        results.append(record)

    return results
