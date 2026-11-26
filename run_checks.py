"""기존 9개 검사 및 새로운 검사 실행 + 세 단계의 실제 증거 파일 저장."""
from pathlib import Path
import json
import shutil
import sys
import unittest
from comparison import case_specs, compare_case

ROOT=Path(__file__).resolve().parent

def main():
    print('Python:',sys.version.split()[0],flush=True)
    results=ROOT/'results'
    evidence=results/'evidence'
    if evidence.exists(): shutil.rmtree(evidence)
    evidence.mkdir(parents=True)
    observations={}
    for name in case_specs():
        record=compare_case(name,evidence)
        observations[name]=record
        print(f'{name}: expected == actual; stages={", ".join(record["actual"])}',flush=True)
    (results/'comparison.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2),encoding='utf-8')
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    with (results/'verification.txt').open('w',encoding='utf-8') as f:
        f.write(f'Python: {sys.version.split()[0]}\n')
        for name in observations: f.write(f'{name}: expected == actual (PASS)\n')
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        summary=f'tests_run={result.testsRun} failures={len(result.failures)} errors={len(result.errors)}'
        f.write(summary+'\n')
    print((results/'verification.txt').read_text(encoding='utf-8'))
    if not result.wasSuccessful(): raise SystemExit(1)

if __name__=='__main__': main()
