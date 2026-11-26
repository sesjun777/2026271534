"""세 단계의 실제 파일과 JSONL 및 오류를 비교한다. 예상값은 규칙에서 별도로 정의."""
from contextlib import chdir
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import tempfile

import before_refactor as before
from stages.refactored.organizer import FileOrganizer as Refactored, ExtensionStrategy as RefExtension
from organizer import FileOrganizer, ExtensionStrategy, DateExtensionStrategy

STAGES = ('before', 'refactored', 'final_extension')
FIXED = datetime(2026, 11, 15, 12, tzinfo=timezone.utc).timestamp()
# 실제 콘텐츠를 비교한다. PDF/JPG 확장자는 분류용 가상 파일이다.
NORMAL = {'report.pdf': b'demo document\n', 'PHOTO.JPG': b'demo image placeholder\n',
          'scores.csv': b'name,score\nA,90\n', 'README': b'no extension example\n'}
NORMAL_PATHS = {'PHOTO.JPG': 'Images/PHOTO.JPG', 'README': 'Others/README',
                'report.pdf': 'Documents/report.pdf', 'scores.csv': 'Data/scores.csv'}


def case_specs():
    return {
        'normal': dict(files=NORMAL, paths=NORMAL_PATHS),
        'empty': dict(files={}, paths={}),
        'missing': dict(files={}, paths={}, source_kind='missing', error='FileNotFoundError'),
        'not_directory': dict(files={}, paths={}, source_kind='file', error='NotADirectoryError'),
        'same_folder': dict(files={'report.pdf': b'x'}, paths={}, same=True, error='ValueError'),
        'collision': dict(files={'report.pdf': b'new'}, paths={'report.pdf':'Documents/report.pdf'},
                          existing={'Documents/report.pdf':b'keep'}, execute_error='FileExistsError'),
        'late_collision': dict(files={'a.txt':b'first', 'z.txt':b'new'},
                               paths={'a.txt':'Documents/a.txt','z.txt':'Documents/z.txt'},
                               existing={'Documents/z.txt':b'keep'}, copied=['a.txt'], execute_error='FileExistsError'),
        'all_categories': dict(files={'clip.mp4':b'video','pack.zip':b'zip','x.bin':b'unknown'},
                               paths={'clip.mp4':'Videos/clip.mp4','pack.zip':'Archives/pack.zip','x.bin':'Others/x.bin'},
                               subfolder=True),
        'date_boundary': dict(files={'nov.pdf':b'nov', 'dec.pdf':b'dec'},
                              paths={'dec.pdf':'2026-12/Documents/dec.pdf','nov.pdf':'2026-11/Documents/nov.pdf'},
                              dates={'nov.pdf':datetime(2026,11,30,23,59,tzinfo=timezone.utc).timestamp(),
                                     'dec.pdf':datetime(2026,12,1,0,0,tzinfo=timezone.utc).timestamp()}),
    }


def snapshot(path):
    """경로별 실제 파일 바이트를 기록. 로그는 별도로 비교."""
    if not path.is_dir():
        return {}
    return {p.relative_to(path).as_posix():p.read_bytes() for p in sorted(path.rglob('*'))
            if p.is_file() and p.name != 'organizer_log.jsonl'}


def json_bytes(mapping):
    # 텍스트가 아닌 파일도 16진수로 비교할 수 있는 표현
    return {k:v.hex() for k,v in mapping.items()}


def plan_rows(plan, stage):
    if stage == 'before':
        return [{k:Path(v).as_posix() if k in ('source','destination') else v for k,v in item.items()}
                for item in plan]
    return [{'source':x.source.as_posix(),'destination':x.destination.as_posix(),'category':x.category} for x in plan]


def attempt(fn):
    try:
        return fn(), None
    except (OSError, ValueError) as exc:
        return None, {'type':type(exc).__name__, 'message':str(exc)}


def run_case(name, stage, evidence=None):
    spec = case_specs()[name]
    with tempfile.TemporaryDirectory() as temp, chdir(temp):
        source, output = Path('input'), Path('output')
        kind = spec.get('source_kind', 'directory')
        if kind == 'directory':
            source.mkdir()
        elif kind == 'file':
            source.write_text('not a directory', encoding='utf-8')
        for filename, content in spec['files'].items():
            file = source / filename
            file.write_bytes(content)
            stamp = spec.get('dates', {}).get(filename, FIXED)
            os.utime(file, (stamp, stamp))
        if spec.get('subfolder'):
            (source/'nested').mkdir()
            (source/'nested'/'ignored.txt').write_bytes(b'ignored')
        if spec.get('same'):
            output = source
        for rel, content in spec.get('existing', {}).items():
            target = output / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        original = snapshot(source)
        initial = snapshot(output)
        initial_output_exists = output.exists()
        if stage == 'before':
            preview = lambda: before.preview_plan(source, output)
            execute = lambda: before.organize_files(source, output)
        elif stage == 'refactored':
            organizer = Refactored(source, output, RefExtension())
            preview, execute = organizer.preview, organizer.execute
        else:
            strategy = DateExtensionStrategy() if stage == 'final_date' else ExtensionStrategy()
            organizer = FileOrganizer(source, output, strategy)
            preview, execute = organizer.preview, organizer.execute
        plan, preview_error = attempt(preview)
        rows = plan_rows(plan, stage) if plan is not None else []
        log = output / 'organizer_log.jsonl'
        preview_clean = (snapshot(output) == initial and output.exists() == initial_output_exists
                         and not log.exists() and snapshot(source) == original)
        _, execution_error = attempt(execute)
        logs = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
        # 시간은 실제 실행마다 다르므로 제거하기 전 UTC 형식 검사를 한다.
        for row in logs:
            assert set(row) == {'source','destination','category','status','time_utc'}
            parsed = datetime.fromisoformat(row['time_utc'])
            assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
        normalized = [{k:(Path(v).as_posix() if k in ('source','destination') else v)
                       for k,v in row.items() if k != 'time_utc'} for row in logs]
        result = {'plan':rows,'preview_error':preview_error,'execute_error':execution_error,
                  'output_files_hex':json_bytes(snapshot(output)), 'log_rows':normalized,
                  'log_exists':log.exists(), 'preview_no_write':preview_clean,
                  'source_unchanged':snapshot(source)==original,
                  'output_exists':output.exists()}
        if evidence is not None:
            dest = evidence / name / stage
            dest.mkdir(parents=True, exist_ok=True)
            if source.is_dir(): shutil.copytree(source, dest/'input', dirs_exist_ok=True)
            if output.is_dir(): shutil.copytree(output, dest/'output', dirs_exist_ok=True)
            (dest/'observed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result


def expected(name):
    spec = case_specs()[name]
    paths = spec['paths']
    rows = [{'source':f'input/{file}','destination':f'output/{path}','category':Path(path).parent.name}
            for file,path in sorted(paths.items(),key=lambda x:x[0].lower())]
    copied = spec.get('copied', [] if spec.get('error') or spec.get('execute_error') else list(paths))
    output = dict(spec.get('existing', {}))
    if spec.get('same'): output.update(spec['files'])
    output.update({paths[file]:spec['files'][file] for file in copied})
    logs = [dict(row,status='copied') for row in rows if Path(row['source']).name in copied]
    return {'plan':rows,'preview_error':spec.get('error'),
            'execute_error':spec.get('error') or spec.get('execute_error'),
            'output_files_hex':json_bytes(output),'log_rows':logs,'log_exists':bool(logs),
            'preview_no_write':True,'source_unchanged':True,
            'output_exists':bool(output)}


def compare_expected(name, result):
    actual = dict(result)
    for key in ('preview_error','execute_error'):
        actual[key] = result[key]['type'] if result[key] else None
    assert actual == expected(name), f'{name}:\nexpected={expected(name)}\nactual={actual}'


def compare_case(name, evidence=None):
    stages = ('final_date',) if name=='date_boundary' else STAGES
    results = {stage:run_case(name,stage,evidence) for stage in stages}
    for result in results.values(): compare_expected(name,result)
    # 예외 유형 뿐 아니라 메시지 및 저장 내용까지 단계 간 동일해야 한다.
    assert all(result==next(iter(results.values())) for result in results.values()), name
    return {'expected':expected(name),'actual':results,'passed':True}
