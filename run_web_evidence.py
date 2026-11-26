"""실제 로컬 서버의 HTTP 응답 및 저장 파일을 results/web에 보존한다."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import json
import os
import re
import shutil
import tempfile
import threading
from web_app import create_server

ROOT=Path(__file__).resolve().parent

def main():
    dest=ROOT/'results/web'
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        shutil.copytree(ROOT/'examples/sample_input',root/'examples/sample_input')
        fixed=datetime(2026,11,15,12,tzinfo=timezone.utc).timestamp()
        for f in (root/'examples/sample_input').iterdir(): os.utime(f,(fixed,fixed))
        server=create_server(root,0)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        thread.start()
        url=f'http://127.0.0.1:{server.server_port}/'
        results=[]
        try:
            with urlopen(url,timeout=5) as res:
                body=res.read().decode('utf-8')
                assert res.status==200
            token=re.search(r'name="token" value="([^"]+)"',body).group(1)
            def submit(action,strategy,output,name,expected_text):
                data=urlencode(dict(token=token,action=action,strategy=strategy,
                    source='examples/sample_input',output=output)).encode()
                with urlopen(url,data,timeout=5) as res:
                    body=res.read().decode('utf-8'); status=res.status
                assert status==200 and expected_text in body
                # 응답의 실제 텍스트를 저장하되, 일회용 토큰만 제거한다. 오프라인 증거임.
                (dest/f'{name}.html').write_text(body.replace(token,'expired-token'),encoding='utf-8')
                return status
            status=submit('preview','extension','web_output','preview','미리보기: 4개 파일')
            assert not (root/'web_output').exists()
            results.append({'action':'preview','http_status':status,'files_planned':4,'output_exists':False})
            for strategy,output,name in [('extension','web_output','copy'),('date','web_date_output','date')]:
                status=submit('execute',strategy,output,name,'복사 완료: 4개 파일')
                actual=root/output
                rows=[json.loads(x) for x in (actual/'organizer_log.jsonl').read_text(encoding='utf-8').splitlines()]
                assert len(rows)==4
                for row in rows: assert Path(row['source']).read_bytes()==Path(row['destination']).read_bytes()
                if strategy=='date': assert (actual/'2026-11/Documents/report.pdf').is_file()
                shutil.copytree(actual,dest/f'{name}_output')
                results.append({'action':name,'http_status':status,'copied_files':4,'jsonl_rows':len(rows),
                                'all_bytes_equal':True,'source_preserved':True})
        finally:
            server.shutdown(); thread.join(); server.server_close()
        (dest/'http_results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('웹 HTTP 증거 저장 완료:',dest)

if __name__=='__main__': main()
