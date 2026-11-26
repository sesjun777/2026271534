from __future__ import annotations

import argparse
from pathlib import Path

from organizer import DateExtensionStrategy, ExtensionStrategy, FileOrganizer


def build_strategy(name: str):
    if name == "extension":
        return ExtensionStrategy()
    if name == "date":
        return DateExtensionStrategy()
    raise ValueError(f"지원하지 않는 분류 방법: {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="파일 자동 정리 도구")
    parser.add_argument("source", help="정리할 입력 폴더")
    parser.add_argument("output", help="복사 결과를 저장할 출력 폴더")
    parser.add_argument(
        "--strategy",
        choices=["extension", "date"],
        default="extension",
        help="extension=확장자 분류, date=수정월+확장자 분류",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="지정하지 않으면 미리보기만 수행한다.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    organizer = FileOrganizer(
        source=Path(args.source),
        output=Path(args.output),
        strategy=build_strategy(args.strategy),
    )

    plan = organizer.execute() if args.execute else organizer.preview()
    mode = "복사 완료" if args.execute else "미리보기"

    print(f"[{mode}] {len(plan)}개 파일")
    for item in plan:
        print(f"{item.source.name} -> {item.destination}")


if __name__ == "__main__":
    main()
