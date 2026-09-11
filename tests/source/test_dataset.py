import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def test_replay_preserves_152_source_values_and_elapsed_time():
    data=json.loads((ROOT/'data/synthetic/current_replay.json').read_text(encoding='utf-8'))
    samples=data['samples']
    assert len(samples)==152
    assert samples[0]['source_row']==7 and samples[-1]['source_row']==158
    assert samples[0]['current_l1']==318
    assert samples[-1]['offset_seconds']==151*900
    for a,b in zip(samples,samples[1:]):
        assert b['offset_seconds']-a['offset_seconds']==900
    for sample in samples:
        assert sample['current_l1']==sample['secondary_ma']*sample['ratio']/1000
        assert sample['source']=='organizer_synthetic_replay'
    assert data['measurements_available']==['current_l1']
    assert set(data['missing_channels']) >= {'temperature','humidity','pd','arc'}

def test_all_sources_have_hashes_without_changing_originals():
    import hashlib
    manifest=ROOT/'data/source/manifest.json'
    if not manifest.exists():
        # Production image deliberately excludes original restricted files.
        import pytest
        pytest.skip('Original source artifacts deliberately excluded from runtime image; run on host')
    for source in json.loads(manifest.read_text(encoding='utf-8')):
        assert hashlib.sha256((ROOT/source['file']).read_bytes()).hexdigest()==source['sha256']
