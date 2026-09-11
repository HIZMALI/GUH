"""Create and verify a small, secret-free Git delta without touching the real index."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '4a0f4c1cae879604a384e91862749fef754abecc'
BLOCKED = {'.git', 'node_modules', '.next', '__pycache__', '.pytest_cache', '.pio',
           'tmp', 'runtime', 'output', 'build', 'dist', '.sites-runtime', 'handoff',
           'test-results', 'test-results-v2', 'playwright-report'}


def git(*args, env=None):
    return subprocess.check_output(['git', '-c', 'core.safecrlf=false', *args], cwd=ROOT,
                                   env={**(env or os.environ), 'GIT_OPTIONAL_LOCKS': '0'})


def allowed(name):
    p = Path(name)
    return (not any(part in BLOCKED for part in p.parts)
            and not (p.name.startswith('.env') and p.name != '.env.example')
            and p.suffix.lower() not in {'.pyc', '.tsbuildinfo', '.db', '.key', '.pem'}
            and not any(word in part.lower() for part in p.parts for word in ('secret', 'credential')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    args = parser.parse_args()
    baseline = git('rev-parse', args.baseline + '^{commit}').decode().strip()
    index_path = Path(git('rev-parse', '--git-path', 'index').decode().strip())
    if not index_path.is_absolute(): index_path = ROOT / index_path
    index_before = index_path.read_bytes() if index_path.exists() else None
    changes = set(git('diff', '--no-renames', '--name-only', '-z', baseline).decode().strip('\0').split('\0'))
    changes.update(git('ls-files', '--others', '--exclude-standard', '-z').decode().strip('\0').split('\0'))
    changes.discard('')
    names = sorted(n for n in changes if allowed(n))
    if not names:
        raise RuntimeError('No eligible delta files')
    # Original source material is immutable and must never be duplicated in the delta.
    sources = [n for n in names if Path(n).suffix.lower() in {'.pdf', '.xlsx'}]
    if sources:
        raise RuntimeError('Unexpected changed source PDF/XLSX: ' + ', '.join(sources))
    config = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
                  if line and not line.startswith('#'))
    secrets = [v.encode() for k, v in config.items()
               if any(word in k for word in ('PASSWORD', 'SECRET', 'TOKEN')) and v]
    if not secrets or any(len(value) < 8 for value in secrets):
        raise RuntimeError('Missing or very short local credentials; refuse an unreliable content scan')
    for name in names:
        path = ROOT / name
        if path.exists():
            path.resolve().relative_to(ROOT.resolve())
            if path.is_symlink() or any(value in path.read_bytes() for value in secrets):
                raise RuntimeError('Unsafe delta content: ' + name)
    destination = ROOT / 'handoff/GridSentinel-v2-delta'
    archive = ROOT / 'handoff/GridSentinel-v2-delta.zip'
    if destination.exists() or archive.exists():
        raise RuntimeError('Handoff already exists; choose a reviewed new output instead of overwriting it')
    destination.mkdir(parents=True)
    work = ROOT / 'tmp'
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='delta-index-', dir=work) as temporary:
        Path(temporary).resolve().relative_to(work.resolve())
        index_env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temporary) / 'snapshot.index')}
        git('read-tree', baseline, env=index_env)
        for offset in range(0, len(names), 50):
            git('add', '-A', '--', *names[offset:offset + 50], env=index_env)
        patch = git('diff', '--cached', '--binary', '--no-ext-diff', '--no-textconv', baseline, env=index_env)
        if any(value in patch for value in secrets):
            raise RuntimeError('Known private credential detected in patch, including removed lines')
        expected_tree = git('write-tree', env=index_env).decode().strip()
        (destination / 'changes.patch').write_bytes(patch)
        check_env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temporary) / 'apply.index')}
        git('read-tree', baseline, env=check_env)
        git('apply', '--cached', '--check', str(destination / 'changes.patch'), env=check_env)
        git('apply', '--cached', str(destination / 'changes.patch'), env=check_env)
        if git('write-tree', env=check_env).decode().strip() != expected_tree:
            raise RuntimeError('Patch result differs from the packaged source snapshot')
    manifest = []
    for name in names:
        source = ROOT / name
        if not source.exists():
            manifest.append({'path': name, 'status': 'deleted'})
            continue
        target = destination / 'changed-files' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        content = target.read_bytes()
        expected_blob = git('rev-parse', f'{expected_tree}:{name}').decode().strip()
        actual_blob = subprocess.check_output(['git', 'hash-object', f'--path={name}', '--stdin'],
                                              cwd=ROOT, input=content).decode().strip()
        if actual_blob != expected_blob:
            raise RuntimeError('File changed after the verified Git snapshot: ' + name)
        manifest.append({'path': name, 'status': 'included', 'bytes': len(content),
                         'sha256': hashlib.sha256(content).hexdigest()})
        if name.startswith('docs/verification/v2'):
            target = destination / 'verification' / Path(name).relative_to('docs/verification')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    (destination / 'BASELINE.txt').write_text(f'Baseline commit: {baseline}\nBranch: codex/gridsentinel-v2\n'
        'V1 working tree was clean before V2 changes. V1 baseline tests are under verification/v2-baseline.\n'
        f'Expected delta tree: {expected_tree}\nPatch application checked against an isolated Git index.\n', encoding='utf-8')
    (destination / 'STATUS.txt').write_bytes(git('status', '--short') + b'\n' + git('diff', '--stat', baseline))
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (destination / 'README.txt').write_text(
        'GridSentinel V2 delta\n\n'
        'Apply only to the BASELINE.txt commit with a reviewed clean working tree.\n'
        '1. Keep the existing private .env and original source PDFs/XLSX.\n'
        '2. Run: git apply --check /absolute/path/changes.patch\n'
        '3. Run: git apply /absolute/path/changes.patch\n'
        '4. Run: python scripts/run_demo.py --presentation --panels 500 --scenario combined_thermal_pd\n'
        '5. Read docs/acceptance.md and docs/verification/v2-summary.json.\n\n'
        'changed-files mirrors only changed/new paths. Deleted files are listed in manifest.json and handled by the patch.\n'
        'verification contains V2 evidence, including the V1 baseline rerun. Runtime caches, secrets, volumes and unchanged sources are excluded.\n'
        'No physical field installation, production SCADA connection, real provider delivery or protection control.\n'
        'Reference hardware/firmware validation limits are documented in the delivered files.\n', encoding='utf-8')
    for path in destination.rglob('*'):
        if path.is_file() and any(value in path.read_bytes() for value in secrets):
            raise RuntimeError('Known private credential detected in generated package content: ' + path.name)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                bundle.write(path, Path(destination.name) / path.relative_to(destination))
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError('ZIP CRC validation failed')
        for name in bundle.namelist():
            if any(value in bundle.read(name) for value in secrets):
                raise RuntimeError('Known private credential detected in ZIP content')
            parts = Path(name).parts
            if any(p in {'.env', '.git', 'node_modules', '.next', '__pycache__', '.pytest_cache', 'tmp'} for p in parts):
                raise RuntimeError('Forbidden ZIP member: ' + name)
    if (index_path.read_bytes() if index_path.exists() else None) != index_before:
        raise RuntimeError('Real Git index changed during packaging; do not claim an isolated handoff')
    print(json.dumps({'zip': str(archive), 'bytes': archive.stat().st_size, 'changed_files': len(manifest),
                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'patch_checked': True,
                      'real_git_index_modified': False, 'secret_scan_passed': True}, ensure_ascii=False))


if __name__ == '__main__':
    main()
