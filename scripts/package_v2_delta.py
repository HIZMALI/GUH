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
BLOCKED = {'.git', 'node_modules', '.next', '__pycache__', '.pytest_cache', '.pio', '.venv', '.cache', '.mypy_cache', '.ruff_cache',
           'tmp', 'runtime', 'output', 'build', 'dist', '.sites-runtime', 'handoff',
           'test-results', 'test-results-v2', 'playwright-report'}


def git(*args, env=None):
    return subprocess.check_output(['git', '-c', 'core.safecrlf=false', *args], cwd=ROOT,
                                   env={**(env or os.environ), 'GIT_OPTIONAL_LOCKS': '0'})


def allowed(name):
    p = Path(name)
    return (not any(part in BLOCKED for part in p.parts)
            and not (p.name.startswith('.env') and p.name != '.env.example')
            and p.suffix.lower() not in {'.pyc', '.tsbuildinfo', '.db', '.key', '.pem', '.zip'}
            and not any(word in part.lower() for part in p.parts for word in ('secret', 'credential')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--final-commit', default='HEAD', help='Committed final HEAD; a clean main working tree is required')
    args = parser.parse_args()
    baseline = git('rev-parse', args.baseline + '^{commit}').decode().strip()
    final_commit = git('rev-parse', args.final_commit + '^{commit}').decode().strip()
    final_tree = git('rev-parse', final_commit + '^{tree}').decode().strip()
    branch = git('branch', '--show-current').decode().strip()
    if branch != 'main' or final_commit != git('rev-parse', 'HEAD').decode().strip():
        raise RuntimeError('Package the current committed main HEAD only')
    if git('status', '--porcelain'):
        raise RuntimeError('Commit all reviewed changes before packaging; working tree must be clean')
    committed_names = set(git('ls-tree', '-r', '--name-only', '-z', final_commit).decode().strip('\0').split('\0'))
    forbidden = sorted(name for name in committed_names if not allowed(name))
    if forbidden:
        raise RuntimeError('Forbidden committed files: ' + ', '.join(forbidden))
    index_path = Path(git('rev-parse', '--git-path', 'index').decode().strip())
    if not index_path.is_absolute(): index_path = ROOT / index_path
    index_before = index_path.read_bytes() if index_path.exists() else None
    changes = set(git('diff', '--no-renames', '--name-only', '-z', baseline, final_commit).decode().strip('\0').split('\0'))
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
    # Scan the complete committed snapshot, not only the changed files.
    for name in sorted(committed_names):
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
        patch = git('diff', '--binary', '--no-renames', '--no-ext-diff', '--no-textconv', baseline, final_commit)
        if any(value in patch for value in secrets):
            raise RuntimeError('Known private credential detected in patch, including removed lines')
        (destination / 'changes.patch').write_bytes(patch)
        check_env = {**os.environ, 'GIT_INDEX_FILE': str(Path(temporary) / 'apply.index')}
        git('read-tree', baseline, env=check_env)
        git('apply', '--cached', '--check', str(destination / 'changes.patch'), env=check_env)
        git('apply', '--cached', str(destination / 'changes.patch'), env=check_env)
        if git('write-tree', env=check_env).decode().strip() != final_tree:
            raise RuntimeError('Patch result differs from the committed final tree')
    manifest = []
    for name in names:
        source = ROOT / name
        if name not in committed_names:
            manifest.append({'path': name, 'status': 'deleted'})
            continue
        target = destination / 'changed-files' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        content = target.read_bytes()
        expected_blob = git('rev-parse', f'{final_tree}:{name}').decode().strip()
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
    summary = json.loads((ROOT / 'docs/verification/v2-evidence.json').read_text(encoding='utf-8'))
    if summary['baseline_commit'] != baseline:
        raise RuntimeError('Evidence baseline does not match the packaged baseline')
    summary.update(final_commit=final_commit, final_tree=final_tree,
                   commit_metadata_scope='Exact committed main HEAD and tree. Generated after commit from tracked v2-evidence.json; measurement timestamps remain unchanged.')
    summary_content = json.dumps(summary, ensure_ascii=False, indent=2).encode('utf-8')
    # Generated identity stays outside the commit to avoid self-referential hashes.
    (ROOT / 'docs/verification/v2-summary.json').write_bytes(summary_content)
    (destination / 'verification/v2-summary.json').write_bytes(summary_content)
    (destination / 'BASELINE.txt').write_text(f'Baseline commit: {baseline}\nBranch: {branch}\n'
        'V1 working tree was clean before V2 changes. V1 baseline tests are under verification/v2-baseline.\n'
        f'Final commit: {final_commit}\nFinal tree: {final_tree}\n'
        'Patch application checked against an isolated Git index; its resulting tree equals the final commit tree.\n', encoding='utf-8')
    (destination / 'STATUS.txt').write_bytes(git('status', '--short') + b'\n' + git('diff', '--stat', baseline))
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    metadata = {'baseline_commit': baseline, 'final_commit': final_commit, 'final_tree': final_tree,
                'patch_sha256': hashlib.sha256(patch).hexdigest(),
                'manifest_sha256': hashlib.sha256((destination / 'manifest.json').read_bytes()).hexdigest(),
                'summary_sha256': hashlib.sha256(summary_content).hexdigest(),
                'generated_summary': 'verification/v2-summary.json',
                'commit_metadata_scope': 'final_commit and final_tree identify the exact committed source; generated delivery metadata embeds this identity after committing.'}
    (destination / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    assert all(summary[key] == metadata[key] for key in ('baseline_commit', 'final_commit', 'final_tree'))
    (destination / 'README.txt').write_text(
        'GridSentinel V2 delta\n\n'
        'Apply only to the BASELINE.txt commit with a reviewed clean working tree.\n'
        '1. Keep the existing private .env and original source PDFs/XLSX.\n'
        '2. Run: git apply --check /absolute/path/changes.patch\n'
        '3. Run: git apply /absolute/path/changes.patch\n'
        '4. Run: python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation\n'
        '5. Copy verification/v2-summary.json from this handoff to docs/verification/v2-summary.json in the repository.\n'
        '6. Read docs/acceptance.md, docs/delivery-integrity.md and docs/verification/v2-summary.json.\n\n'
        'changed-files mirrors only changed/new paths. Deleted files are listed in manifest.json and handled by the patch.\n'
        'verification contains V2 evidence, including the V1 baseline rerun, plus a generated summary with the final Git identity. The summary is ignored by Git; v2-evidence.json is tracked.\n'
        'Runtime caches, secrets, volumes and unchanged sources are excluded.\n'
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
    if git('status', '--porcelain') or git('rev-parse', 'HEAD').decode().strip() != final_commit:
        raise RuntimeError('Repository changed while packaging')
    archive.with_suffix('.zip.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n', encoding='utf-8')
    verification = {'baseline_commit': baseline, 'final_commit': final_commit, 'final_tree': final_tree, 'zip': str(archive), 'bytes': archive.stat().st_size, 'changed_files': len(manifest),
                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'patch_checked': True,
                      'real_git_index_modified': False, 'secret_scan_passed': True,
                      'exclusion_check_passed': True, 'zip_crc_passed': True, 'manifest_blob_hashes_verified': True,
                      'patch_tree_equals_final_tree': True, 'git_status_clean': True}
    archive.with_suffix('.zip.verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(verification, ensure_ascii=False))


if __name__ == '__main__':
    main()
