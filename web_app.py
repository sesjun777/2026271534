"""로컬 브라우저용 화면. 표준 라이브러리만 사용하며 핵심 정리 코드를 재사용한다."""
from argparse import ArgumentParser
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import parse_qs

from main import build_strategy
from organizer import FileOrganizer, PlanItem

ROOT = Path(__file__).resolve().parent


def render_page(token, source='examples/sample_input', output='web_output', strategy='extension',
                message='입력 폴더와 출력 폴더를 확인한 뒤 미리보기를 실행하세요.', items=(), error=False):
    e = escape
    rows = ''.join(f'<tr><td>{e(x.source.name)}</td><td>{e(x.category)}</td>'
                   f'<td>{e(x.destination.as_posix())}</td></tr>' for x in items)
    if not rows:
        rows = '<tr><td colspan="3">표시할 파일 없음</td></tr>'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>파일 자동 정리 도구</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#f3f6fa;color:#182b3c;font:16px system-ui,sans-serif}} main{{max-width:960px;margin:28px auto;padding:0 22px}} h1{{font-size:29px;margin:0 0 7px}} p{{line-height:1.5}} .panel{{background:white;border:1px solid #dce3eb;border-radius:12px;padding:22px;margin-top:18px}} label{{display:block;font-weight:650;margin:12px 0 5px}} input,select{{width:100%;padding:10px;border:1px solid #aab8c6;border-radius:6px;font:inherit}} .buttons{{display:flex;gap:12px;margin-top:20px}} button{{padding:11px 20px;border-radius:7px;border:1px solid #145b81;background:white;color:#145b81;font:inherit;font-weight:650;cursor:pointer}} .primary{{background:#145b81;color:white}} .status{{border-left:4px solid #145b81;padding:9px 12px;background:#eef6fb;overflow-wrap:anywhere}} .error{{border-color:#a62222;background:#fff0f0;color:#8e2222}} table{{border-collapse:collapse;width:100%;font-size:14px}} th,td{{padding:10px;text-align:left;border-bottom:1px solid #dde4ec;overflow-wrap:anywhere}} th{{background:#f1f5f8}} small{{color:#486275}} @media(max-width:600px){{main{{padding:0 10px}} .panel{{padding:12px}}}}
</style></head><body><main><h1>파일 자동 정리 도구</h1><small>Strategy · 로컬 실행 · 원본 보존</small><section class="panel"><form method="post" action="/">
<input type="hidden" name="token" value="{e(token,quote=True)}">
<label for="source">입력 폴더 (프로젝트 기준)</label><input id="source" name="source" value="{e(source,quote=True)}" required>
<label for="output">출력 폴더 (프로젝트 기준)</label><input id="output" name="output" value="{e(output,quote=True)}" required>
<label for="strategy">분류 규칙</label><select id="strategy" name="strategy"><option value="extension" {'selected' if strategy=='extension' else ''}>확장자별 분류</option><option value="date" {'selected' if strategy=='date' else ''}>수정월(UTC) + 확장자별 분류</option></select>
<div class="buttons"><button name="action" value="preview">미리보기</button><button class="primary" name="action" value="execute">실제 복사 및 기록</button></div>
<p><small>미리보기는 저장하지 않습니다. 실제 복사 시 같은 이름의 기존 파일은 덮어쓰지 않으며, 처리 기록은 출력 폴더의 organizer_log.jsonl에 저장합니다.</small></p></form></section>
<section class="panel"><h2 style="margin-top:0;font-size:20px">처리 결과</h2><p class="status {'error' if error else ''}" role="status">{e(message)}</p><table><thead><tr><th>파일</th><th>분류</th><th>목적 경로</th></tr></thead><tbody>{rows}</tbody></table></section></main></body></html>'''


def checked_path(value, root):
    if not value.strip():
        raise ValueError('폴더 경로를 입력하세요.')
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('웹 화면에서는 프로젝트 폴더 내부 경로만 사용할 수 있습니다.')
    return candidate.relative_to(root)


def create_server(root=ROOT, port=8000):
    root = Path(root).resolve()
    token = token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def send_page(self, status, body):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path != '/':
                self.send_error(404)
                return
            self.send_page(200,render_page(token))

        def do_POST(self):
            if self.path != '/':
                self.send_error(404)
                return
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 < size <= 16000:
                    raise ValueError('요청 크기가 올바르지 않습니다.')
                form = parse_qs(self.rfile.read(size).decode('utf-8'), keep_blank_values=True)
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            get = lambda key, default='': form.get(key,[default])[0]
            if get('token') != token:
                self.send_error(403)
                return
            source_text, output_text = get('source'), get('output')
            strategy, action = get('strategy'), get('action')
            try:
                source = root / checked_path(source_text,root)
                output = root / checked_path(output_text,root)
                if action not in ('preview','execute'):
                    raise ValueError('지원하지 않는 작업입니다.')
                obj = FileOrganizer(source,output,build_strategy(strategy))
                items = obj.preview()
                # 웹의 작업 범위를 프로젝트 내부로 제한한다. 링크를 통한 경로 우회는 거부한다.
                if any(x.source.is_symlink() or not x.destination.resolve().is_relative_to(root)
                       or x.destination.is_symlink() for x in items):
                    raise ValueError('심볼릭 링크 파일 또는 외부 대상 경로는 지원하지 않습니다.')
                log = output / 'organizer_log.jsonl'
                if log.is_symlink() or not log.resolve().is_relative_to(root):
                    raise ValueError('외부 로그 경로는 지원하지 않습니다.')
                if action == 'execute':
                    items = obj.execute()
                message = f'{"복사 완료" if action=="execute" else "미리보기"}: {len(items)}개 파일'
                display_items = [PlanItem(x.source.relative_to(root), x.destination.relative_to(root), x.category) for x in items]
                self.send_page(200,render_page(token,source_text,output_text,strategy,message,display_items))
            except (OSError,ValueError) as exc:
                self.send_page(400,render_page(token,source_text,output_text,strategy,
                    f'{type(exc).__name__}: {exc}',error=True))

    # 외부 네트워크에서 접근할 수 없도록 루프백 주소에만 연결한다.
    return HTTPServer(('127.0.0.1',port),Handler)


def main():
    parser=ArgumentParser(description='파일 자동 정리 도구 웹 화면')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    with create_server(port=args.port) as server:
        print(f'브라우저에서 http://127.0.0.1:{server.server_port}/ 을 여세요. 종료: Ctrl+C',flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__=='__main__':
    main()
