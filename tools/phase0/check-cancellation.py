"""Probe upstream reference cancellation boundaries; no production worker code."""
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'running', 'runnerSha256': sha(Path(__file__)),
              'backend': 'torch-eager', 'device': 'cuda', 'cases': [],
              'networkAttempts': [],
              'scope': 'Upstream Python callbacks only; not UI Stop, process supervision, or a cancellation deadline guarantee'}
    for key in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY'):
        os.environ[key] = '1'

    def audit(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname'}:
            report['networkAttempts'].append(event)
            raise RuntimeError('Offline probe blocked ' + event)

    sys.addaudithook(audit)
    pipe = None
    try:
        import numpy as np
        import torch
        from yue2 import YuE2Pipeline, SymbolicPlan, SemanticResult
        import yue2
        source = json.loads((ROOT / 'docs/validation/phase0/reference-source-verification.json').read_text(encoding='utf-8-sig'))
        for module in source['modules']:
            assert sha(Path(yue2.__file__).parent / module['path']) == module['sha256'], 'Source changed'
        report['engineSource'] = source['engineSource']
        lock_path = ROOT / 'docs/validation/phase0/model-profiles.lock.json'
        report['modelLockSha256'] = sha(lock_path)
        profile = json.loads(lock_path.read_text(encoding='utf-8-sig'))['profiles'][0]
        folders = {}
        for asset in profile['assets']:
            folder = ROOT / '.phase0/models' / asset['repository'] / asset['revision']
            path = folder / asset['path']
            assert path.stat().st_size == asset['bytes'] and sha(path) == asset['sha256'], 'Asset changed'
            folders[asset['role']] = folder
        saved = ROOT / '.phase0/runs/windows-short-eager/take-1'
        result = json.loads((saved / 'result.json').read_text())
        assert sha(saved / 'semantic.npy') == result['artifacts']['semantic.npy']['sha256'], 'Semantic artifact changed'
        plan = SymbolicPlan.load(saved)
        semantic = SemanticResult(plan, np.load(saved / 'semantic.npy', allow_pickle=False).tolist(), {}, False)
        request = json.loads((ROOT / 'tools/phase0/requests/short.json').read_text())
        report['requestSha256'] = sha(ROOT / 'tools/phase0/requests/short.json')
        report['semanticSha256'] = sha(saved / 'semantic.npy')
        report['torch'] = torch.__version__
        report['gpu'] = torch.cuda.get_device_name(0)
        for name in ('pre-cancelled-planning', 'planning-after-8-tokens', 'semantic-after-8-tokens', 'acoustic-after-3-checks'):
            pipe = YuE2Pipeline.from_pretrained(str(folders['generator']), vae=str(folders['decoder']),
                local_files_only=True, device='cuda', backend='torch-eager', progress=False)
            state = {'tokens': 0, 'checks': 0, 'requestedAt': None}
            start = time.perf_counter()
            if name == 'pre-cancelled-planning':
                state['requestedAt'] = start

            def token(phase, value):
                state['tokens'] += 1
                if state['tokens'] == 8:
                    state['requestedAt'] = time.perf_counter()

            def cancelled():
                state['checks'] += 1
                if name == 'acoustic-after-3-checks' and state['checks'] == 3:
                    state['requestedAt'] = time.perf_counter()
                return state['requestedAt'] is not None

            case = {'name': name, 'status': 'failed-no-interruption'}
            try:
                if name.startswith('semantic'):
                    pipe.generate_semantic(plan, cancelled=cancelled, on_token=token)
                elif name.startswith('acoustic'):
                    pipe.synthesize(semantic, cancelled=cancelled)
                else:
                    pipe.plan(**request, cancelled=cancelled, on_token=token)
            except InterruptedError as error:
                case.update(status='passed', message=str(error),
                    cancellationToExceptionSeconds=time.perf_counter() - state['requestedAt'])
            case.update(elapsedSeconds=time.perf_counter() - start, tokens=state['tokens'], checks=state['checks'])
            pipe.close()
            pipe = None
            gc.collect()
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            case['cudaAllocatedAfterCloseBytes'] = torch.cuda.memory_allocated()
            case['cudaReservedAfterCloseBytes'] = torch.cuda.memory_reserved()
            report['cases'].append(case)
            print(json.dumps(case), flush=True)
        report['status'] = 'passed' if all(c['status'] == 'passed' for c in report['cases']) else 'failed'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
        raise
    finally:
        if pipe is not None:
            pipe.close()
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
