# 파일 자동 정리 도구 | 과제2

다운로드·과제 폴더의 최상위 파일을 확장자별로 분류하고, 선택적으로 UTC 수정월까지 포함해 복사하는 Python 프로젝트입니다. 미리보기와 실제 복사/JSONL 기록을 지원합니다. 원본을 삭제하거나 이동하지 않습니다.

## 1. 실행 환경
- Python 3.12 이상 권장. 실제 검사 환경: Python 3.13.5.
- 외부 패키지 없음. requirements.txt는 표준 라이브러리만 사용함을 표시합니다.
- ZIP을 풀고 `file_organizer` 폴더 안에서 아래 명령을 실행합니다. Windows에서 `python` 대신 `py -3` 사용 가능.
- 예시 `report.pdf`, `PHOTO.JPG` 등은 확장자 분류 및 바이트 복사를 위한 작은 가상 파일입니다. 실제 PDF나 사진 뷰어로 여는 용도가 아닙니다.

## 2. 터미널 실행
```sh
python --version
python main.py examples/sample_input organized --strategy extension
python main.py examples/sample_input organized --strategy extension --execute
python main.py examples/sample_input organized_by_date --strategy date --execute
```
첫 명령은 미리보기만 수행합니다(출력 폴더를 만들지 않음). `--execute`가 있어야 복사합니다. 실제 로그는 출력 폴더의 `organizer_log.jsonl`입니다. 날짜 분류는 각 파일의 실제 수정 시각을 읽으므로 ZIP 해제 환경에 따라 날짜 폴더가 달라질 수 있습니다. 검사는 수정 시각을 고정합니다.

## 3. 웹 화면 (선택 가산점)
```sh
python web_app.py
```
브라우저에서 http://127.0.0.1:8000/ 접속. 포트 사용 중이면 `python web_app.py --port 8001` 실행 후 해당 포트로 접속합니다. 종료는 터미널에서 Ctrl+C.

1. 입력 폴더 `examples/sample_input`, 출력 폴더 `web_output`을 확인합니다. 웹 화면에서는 프로젝트 내부의 폴더만 허용합니다. 직접 만든 파일도 프로젝트 내 별도 입력 폴더에 넣어 사용할 수 있습니다.
2. 확장자별 분류 또는 수정월(UTC)+확장자 분류를 선택합니다.
3. **미리보기**를 눌러 경로를 확인합니다. 출력 폴더는 생성되지 않습니다.
4. **실제 복사 및 기록**을 누릅니다. 결과 표와 JSONL을 확인합니다. 날짜 분류를 시험할 때는 새 출력 폴더(예: `web_date_output`)를 입력하세요. 기존 대상 파일이 있으면 덮어쓰지 않고 오류를 표시합니다.

웹은 `main.build_strategy()`와 `FileOrganizer`를 직접 호출하는 별도의 입력·출력 화면이며 분류/복사/기록 로직을 다시 구현하지 않았습니다. 루프백 주소에만 연결되는 로컬 개발용 프로그램입니다. 인터넷에 공개하지 마세요.

### 웹 동작 근거
`python run_web_evidence.py`는 실제 HTTP 서버를 실행하여 미리보기, 두 분류 방식의 복사 요청을 보내고 결과와 바이트 동일성을 검사합니다. `results/web/http_results.json`, `preview.html`, `copy.html`, `date.html`, `copy_output/`, `date_output/`에 실제 응답·복사 결과·JSONL이 저장됩니다. HTML은 종료된 서버의 응답 기록으로, 버튼을 작동시키려면 위 실행 절차를 따라야 합니다. 토큰만 만료 문자열로 치환했습니다. 이 환경에서는 브라우저 직접 접속이 제한되어 브라우저 화면 캡처는 없으며, HTTP 요청/응답과 실제 파일로 검증했습니다.

## 4. 구조 개선 전·후·기능 추가 비교
- A (구조 개선 전): `before_refactor.py`의 `preview_plan`, `organize_files`. 기존 조건문에 분류가 고정됨.
- B (구조 개선 후): `stages/refactored/`의 독립 실행 가능한 확장자 Strategy 버전. `python -m stages.refactored.main examples/sample_input refactored_output --execute`로 실행 가능.
- C (기능 변경 후): `main.py`, `organizer/`. 기존 extension 규칙을 유지하며 date 추가. `core.py`, `models.py`, `logger.py`는 B와 C에서 동일한 바이트인지 테스트합니다. `main.py`의 `build_strategy()`와 `parse_args()`에 날짜 선택 연결을 추가한 것이 기능 변경입니다.
- `web_app.py`는 C의 선택 확장 화면입니다.

## 5. 검사 방법과 증거
```sh
python run_checks.py
python -m unittest discover -s tests -v
python run_web_evidence.py
```
`run_checks.py`는 임시 폴더에서 동일한 상대 경로 `input`, `output`과 동일 파일 내용으로 A/B/C(extension)를 독립 실행합니다. 예상값은 규칙을 바탕으로 코드 실행 전에 `comparison.py`에서 정의했습니다. 분류 계획, 출력 파일의 실제 바이트, JSONL 기록 내용, 예외 종류와 메시지, 미리보기 무저장, 원본 보존을 비교합니다. 정상·빈 폴더·누락 폴더·경로가 파일·동일 경로·기존 파일 충돌·중간 충돌·나머지 범주 및 하위 폴더 제외의 8개 기존 상황을 각 3단계에서 검사하고 C(date)의 월 경계 사례를 별도 검사합니다.

- `results/comparison.json`: 예상값과 단계별 실제 결과 전체. 바이트는 hex로 저장(원본 파일도 증거에 포함).
- `results/evidence/<case>/<stage>/`: 실제 입력·출력 파일, JSONL 원문 및 observed.json. 실패 시 생성되지 않은 출력/로그는 존재하지 않는 상태 그대로 보존합니다. 절대 임시 경로 대신 동일한 상대 경로를 사용했습니다.
- JSONL의 `time_utc`는 실행마다 다르므로 원문을 보존한 뒤 UTC 형식·오프셋을 검사하고 비교에서는 제외합니다. 나머지 네 필드는 정확히 비교(Windows 경로 구분자는 POSIX 표기로 정규화).
- `results/verification.txt`: 기존 9개 검사, 새 비교/단계 검사 10개, 웹 HTTP 검사 4개, CLI 검사 2개의 이름 및 실제 실행 결과. 합계 25개.
- `results/web/`: 실제 HTTP 응답과 저장 결과.

## 6. 분류 기준과 선택 이유
| 확장자 | 폴더 |
|---|---|
| .pdf .docx .txt .md | Documents |
| .jpg .jpeg .png .gif | Images |
| .csv .json .xlsx | Data |
| .mp4 .mov | Videos |
| .zip .tar .gz | Archives |
| 기타 / 확장자 없음 | Others |

대표적인 학업 파일 유형을 구분해 여러 분류 분기를 검증하고, 나머지는 Others로 분류합니다. 파일 이름의 마지막 확장자를 소문자로 변환합니다. 복사는 반복 검사 중 원본 보존에 유리합니다. 재귀 탐색은 제외하여 범위를 제한했고, JSONL은 외부 DB 없이 파일별 기록을 한 줄씩 추가할 수 있어 선택했습니다. 2026-11-15와 11월 30일/12월 1일은 테스트 재현과 월 경계 검증을 위한 값입니다. 자세한 근거는 `docs/DESIGN_DECISIONS.md`에 있습니다.

## 7. 파일 구성
```text
file_organizer/
  before_refactor.py           # A: 기본 프로그램
  stages/refactored/           # B: 독립적인 리팩터링 버전
  organizer/                  # C: core, strategies, models, logger
  main.py                     # CLI
  web_app.py                  # 실제 로컬 웹 화면
  comparison.py               # 규칙 기반 기대값 및 3단계 비교
  run_checks.py               # 증거 저장 + 전체 검사
  run_web_evidence.py         # HTTP 응답/저장 증거
  tests/                      # 기존 및 추가 단위·통합 검사
  examples/sample_input/      # 가상 예제 파일
  results/                    # 실제 결과와 증거 원본
  docs/                       # AI 기록, 설계 근거, GitHub 안내
  requirements.txt
  README.md
```

## 8. 한계와 주의점
- 최상위 파일만 처리하고, 내용이 아닌 확장자로 분류합니다. 복사 중 오류가 나면 이미 성공한 파일과 기록이 남습니다. 전체 작업의 원자적 취소(rollback)는 지원하지 않습니다.
- 기존 대상 파일을 덮어쓰지 않는 정책은 순차 실행 및 일반 파일을 전제로 합니다. CLI는 링크·동시 변경·권한·디스크 오류 전반에 대한 안전 보장을 하지 않습니다. 개인 원본보다 테스트 복사본으로 먼저 확인하세요.
- 날짜는 수정일의 UTC 기준 월입니다. 생성일이나 한국 시간 기준 분류는 지원하지 않습니다.
- GitHub 공개 저장소는 아직 등록하지 않았습니다. 실제 저장소를 생성한 뒤 접근 가능한 URL을 README에 기록해야 선택 가산점을 신청할 수 있습니다. `docs/GITHUB_UPLOAD.md` 참조.

## 9. 참고 및 AI 사용
과제 안내 및 7-3 반복문과 Strategy 패턴, 9-1 소프트웨어 아키텍처, 10주차 코딩실습(검사·클래스·모듈·Factory), 10-1 Git과 QA, 11-2 상속과 합성을 참고했습니다. 강의의 개념을 적용한 프로젝트 코드 초안·보완·실행 검사는 ChatGPT의 도움으로 작성했습니다. 구체적 기록은 `docs/AI_USAGE.md`를 참조하세요.
