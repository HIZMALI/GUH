"""Aggregate actual V2 evidence. Missing or failed required evidence stops reporting."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / 'docs/verification'


def read(name):
    return json.loads((PROOF / name).read_text(encoding='utf-8'))


def junit(name):
    root = ET.parse(PROOF / name).getroot()
    suites = list(root.iter('testsuite'))
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
    counts['seconds'] = round(sum(float(s.get('time', 0)) for s in suites), 3)
    counts['evidence'] = name
    assert counts['tests'] > 0 and counts['failures'] == counts['errors'] == 0, name
    return counts


def main():
    frontend, stack, load, runtime = [read(n) for n in ['v2-frontend-summary.json', 'v2-stack.json', 'v2-load.json', 'v2-runtime.json']]
    firmware, presentation = read('v2-firmware-final.json'), read('v2-final-runtime.json')
    cli = read('v2-cli-compatibility.json')
    assert cli['legacy_command']['passed'] and cli['presentation_command']['passed']
    index_proof = read('v2-history-index.json')
    assert index_proof['passed']
    final_ui = read('v2-frontend-final-smoke.json')
    assert final_ui['passed'] and final_ui['console_errors'] == [] and final_ui['scale_version'] == 'v2'
    for key, value in {'total': 500, 'normal': 500, 'offline': 0, 'open_alarms': 0}.items():
        assert final_ui['fleet'][key] == presentation['fleet'][key] == value
    policy = read('v2-frontend-observations.json')['notification_policy_v2']
    assert policy['ATTENTION']['notifications'] == 0 and policy['ATTENTION']['channels'] == []
    assert policy['WARNING']['notifications'] == 2 and set(policy['WARNING']['channels']) == {'sms_mock', 'whatsapp_mock'}
    assert all(policy[state]['persistent_alarm'] for state in ['ATTENTION', 'WARNING'])
    hardware = json.loads((ROOT / 'hardware/pcb/verification.json').read_text(encoding='utf-8'))
    assert frontend['unique_passed'] == frontend['unique_tests'] == 13
    assert frontend['final_regression_complete'] is True and frontend['final_regression']['expected'] == 13
    assert len(stack['checks']) == 11 and all(c['passed'] for c in stack['checks'])
    assert len(load['cases']) == 6 and all(c['passed'] for c in load['cases'])
    assert sum(c['committed'] for c in load['cases']) == 6800
    assert all(c['passed'] for c in runtime['checks']) and presentation['passed']
    assert firmware['host_core']['status'] == hardware['artifact_checks']['status'] == 'PASS'
    projected = json.loads((ROOT / 'apps/web/src/data/scale-proof.json').read_text(encoding='utf-8'))
    assert projected['version'] == 'v2' and projected['source_sha256'] == hashlib.sha256((PROOF / 'v2-load.json').read_bytes()).hexdigest()
    assert final_ui['scale_source_sha256'] == projected['source_sha256']
    screenshot_names = ['fleet', 'panel-clean', 'early-warning', 'scada-bank500', 'scale-value', 'notifications', 'installation', 'attention-policy', 'warning-policy']
    screenshots = [{'path': 'docs/verification/v2-' + n + '.png', 'sha256': hashlib.sha256((PROOF / ('v2-' + n + '.png')).read_bytes()).hexdigest()} for n in screenshot_names]
    measured = runtime['measurements']
    assert measured['combined_critical_seconds'] <= 75 and measured['arc_seconds'] <= 20
    # A tracked file cannot embed the hash of its own containing commit/tree.
    # Packaging adds final identity to the ignored v2-summary.json after commit.
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_WITH_EXPLICIT_HARDWARE_LIMITS',
              'baseline_commit': '4a0f4c1cae879604a384e91862749fef754abecc', 'baseline': read('v2-baseline/summary.json'),
              'python_tests': junit('v2-python-tests.xml'), 'container_tests': junit('v2-python-container-tests.xml'),
              'container_method': 'Production Python image/dependencies; full repository mounted read-only for source and hardware artifact tests; report directory writable. Original hash check runs here, unlike the V1 runtime-image-only skip.',
              'frontend_tests': {'unique_tests': 13, 'passed': 13, 'evidence': 'v2-frontend-summary.json', 'final_full_run': frontend['final_regression']},
              'frontend_final_smoke': final_ui,
              'frontend_tco_tests': {'passed': 5, 'evidence': 'v2-frontend-verification.md'},
              'stack_tests': {'passed': 11, 'evidence': 'v2-stack.json'},
              'load_test': {'passed_cases': 6, 'committed': 6800, 'expected': 6800, 'evidence': 'v2-load.json', 'earlier_runs': ['v2-load-before-history-projection.json', 'v2-load-before-scenario-index.json'], 'legacy_history_index': index_proof, 'cases_500': [c for c in load['cases'] if c['devices'] == 500]},
              'focused_demo_duration_seconds': measured['combined_critical_seconds'], 'arc_event_duration_seconds': measured['arc_seconds'],
              'focused_demo_evidence': 'v2-runtime.json', 'scada_pnl500_roundtrip': presentation['scada_pnl500'],
              'scada_pnl500_host_port': presentation['scada_host_pnl500_port'],
              'cli_compatibility': cli, 'notification_policy': {'version': 2, 'attention_mock_channels': [], 'warning_mock_channels': ['sms_mock', 'whatsapp_mock'], 'browser_evidence': 'v2-frontend-observations.json', 'ui_screenshots': ['v2-attention-policy.png', 'v2-warning-policy.png']}, 'legacy_preservation': read('v2-legacy-preservation.json'), 'firmware_build_status': firmware,
              'hardware_deliverable_status': hardware, 'presentation_ready': presentation, 'screenshots': screenshots,
              'limitations': ['All observations synthetic; no physical field or institutional SCADA connection.',
                  'ESP32 target build NOT_RUN; physical HAL implementation and live-data API normalizer are not implemented.',
                  'KiCad absent; EDA-neutral artifacts, no ERC/DRC, manufactured board or environmental/EMC certification.',
                  'Short burst performance; single API process; no long soak or production SLO guarantee.',
                  'No real SMS/WhatsApp, calibrated PD, RF coverage, battery lifetime, price or ROI claims.',
                  'No breaker trip, device writes, TVOC reset or protection control.']}
    (PROOF / 'v2-evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    # Preserve the complete earlier V1 sections; regenerate only this script's V2 section.
    acceptance = ROOT / 'docs/acceptance.md'
    marker = '\n## V2 Hackathon Readiness\n'
    original = acceptance.read_text(encoding='utf-8').split(marker)[0].rstrip()
    acceptance.write_text(original + '\n' + marker + f'''

Kanıt özeti tarihi UTC: {result['recorded_at']}. V2 temel commit'i `{result['baseline_commit']}`; çalışma öncesi temiz V1 testleri [ayrı baseline kaydında](verification/v2-baseline/summary.json). Git'te izlenen toplu kanıt [v2-evidence.json](verification/v2-evidence.json); commit kimliği içeren `v2-summary.json` paketleme sonrasında üretilir. [Teslim bütünlüğü](delivery-integrity.md).

| Kabul başlığı | Gerçek sonuç | Kanıt / sınır |
|---|---|---|
| Jüri gereksinim izlenebilirliği | PASS: kaynak/uygulama/demo/test/sınır ayrı 6 sütun | [İzlenebilirlik](requirements-traceability.md), [jüri listesi](jury-checklist.md) |
| Hızlı 500 pano demosu | PASS: combined {measured['combined_critical_seconds']:.3f}s, arc {measured['arc_seconds']:.3f}s | [Gerçek Docker/MQTT](verification/v2-runtime.json); 499 arka plan pano ilerledi, 0 offline |
| Temiz current-run UX / tüm geçmiş | PASS | API isolation+pagination, Chromium; 237.402 eski telemetry satırı ve içerik digest'i korundu |
| Erken uyarı | PASS: warning 21 → critical 31, fark 10 sentetik adım | Yapısal kalıcı event ve UI; saha öngörü süresi değildir |
| Aksiyon matrisi | PASS: tek policy/API/UI | [Politika](operations/action-matrix.md); ATTENTION 0 bildirim, WARNING 2 mock kanal; dedupe, audit; fiziksel kontrol yok |
| Tam 500 SCADA adresleme | PASS: 3 bank / 38 Modbus testi; PNL-500 bank 3 / port 1504 / unit 6 | 500 ayrı localhost TCP fixture yanıtı + canlı altı sınır; write/invalid/pending/stale reddi |
| PCB/card çıktısı | PASS artefact: 31 connector pini, 199 net düğümü | [Carrier](../hardware/pcb/README.md), 9 şema/harita testi; EDA-neutral, üretilmedi, ERC/DRC NOT_RUN |
| MCU kaynak kodu | PASS source + C++17 host 7 grup / {firmware['host_core']['assertions']} kontrol | [Firmware](hardware/firmware.md), [hash/komut](verification/v2-firmware-final.json); ESP32 hedef build NOT_RUN |
| Çevresel/manyetik plan | PASS belge kapsamı | [Kaynaklı plan](hardware/environmental-emc-plan.md); fiziksel EMC/thermal/IP testleri yapılmadı |
| Maliyet/fayda ve paketler | PASS model/UI/5 TCO sınır testi | [Maliyet](cost-benefit.md); boş girdide fiyat/ROI yok |
| Yenilikçilik | PASS teknik karşılık/kanıt eşlemesi | [12 teknik fark](innovation.md), Yaygınlaştırma |
| Kurulum/kesinti matrisi | PASS görünür A/B/C ve H1 tutarlılığı | [Kurulum](installation-matrix.md); sağ yardımcı TH-A/H1, güvenli saha keşfi bekler |
| Host Python regresyon | **{result['python_tests']['passed']} PASS**, {result['python_tests']['seconds']:.2f}s | [JUnit](verification/v2-python-tests.xml); 62 V1 + {result['python_tests']['passed'] - 62} yeni test |
| Container Python regresyon | **{result['container_tests']['passed']} PASS**, {result['container_tests']['seconds']:.2f}s | [JUnit](verification/v2-python-container-tests.xml); üretim Python ve bağımlılık image’ı, repo read-only bind; kaynak hash testi de çalışır |
| Frontend regresyon | **13 benzersiz PASS**, TCO 5 PASS | [Son tam koşu](verification/v2-frontend-summary.json), son UI smoke |
| Gerçek servis/kesinti | **11 PASS** | [Stack](verification/v2-stack.json): API/DB/MQTT yeniden başlatma, DB outage mesajının tam 1 commit'i |
| 100 / 250 / 500 HTTP + MQTT yeniden yük | **6 PASS, 6800 / 6800 commit** | [Ham V2](verification/v2-load.json), [V1 ile birlikte performans](performance.md); kısa burst |
| Sunuma hazır son durum | PASS: 500 NORMAL / 0 offline / 0 current open alarm; PNL-001 normal/güncel/0 alarm, rate 1200 | [Son runtime](verification/v2-final-runtime.json), [son tarayıcı](verification/v2-frontend-final-smoke.json) |

Servis doğrulaması SCADA için bounded readiness ve DB connect/pool/statement/socket/lock/DNS sınırlarını kapsar. Salt-okuma yolu maintenance yazma kilidinden ayrıdır; stale risk/policy ve kalıcı alarm tick davranışı korunur. İlk denemelerdeki readiness ve DB toparlanma sorunları giderildikten sonra beş regresyon sınırı ve son gerçek 11 servis kontrolü geçti. Önceki denemeler Git geçmişinde, güncel sonuç [stack kaydında](verification/v2-stack.json) bulunur.

V1 container-image testi kaynak originals image'a alınmadığı için 1 SKIP idi. V2 tam container doğrulaması, kaynaklar/hardware artefact'ları için repo read-only mount kullandığından hash testi de PASS; bu farklılık bilerek kayıtlıdır. Üçüncü taraf Starlette/AnyIO deprecation ve SQLite expression-index reflection uyarıları uygulama test hatası değildir. SQLite indeks adları doğrudan okunur; iki açılış ve mevcut veride migration testleri indeksin tekrar oluşturulmadığını doğrular.

Referans firmware envelope'u mevcut synthetic demo API'sine bağlanmadı; fiziksel UART/BLE/Ethernet/NVM/watchdog/MQTT adapter implementasyonu ve canlı veri normalizer’ı henüz yapılmamıştır. Host testi ESP32 firmware build/flash değildir. PCB sertifikası, gerçek PD pC, RF kapsama/pil ömrü, gerçek SMS/WhatsApp, kurum SCADA bağlantısı, fiyat/ROI veya kesici kumandası iddiası yoktur. Tek API süreci kullanılır; uzun soak, yedek dönüşü, gerçek saha commissioning ve çoklu-worker koordinasyonu ayrıca gerekir.

Delta paketleyici `scripts/package_v2_delta.py`: V1 base üzerine binary patch uygulanabilirliği, normalizasyon sonrası changed-files blob eşitliği, patch+ZIP known-secret taraması ve CRC kontrolü yapar; gerçek Git index değişmez. Çıktı `handoff/GridSentinel-v2-delta.zip`; değişmeyen PDF/Excel, `.env`, cache ve bağımlılıklar dışarıda bırakılır.
''', encoding='utf-8')
    performance = ROOT / 'docs/performance.md'
    perf_marker = '\n## V2 yeniden ölçümü\n'
    rows = []
    for case in load['cases']:
        rows.append(f"| {case['devices']} | {case['transport'].upper()} | {case['committed']}/{case['expected']} | {case['committed_frames_per_second']:.2f} | {case['producer_request_or_puback_ms']['p95']:.2f} | {case['source_to_ingestion_received_ms']['p95']:.2f} | {case['fleet_api_ms']['p95']:.2f} |")
    baseline_load = read('v2-baseline/load.json')
    first_load = read('v2-load-before-history-projection.json')
    baseline_cases = {(c['devices'], c['transport']): c for c in baseline_load['cases']}
    first_cases = {(c['devices'], c['transport']): c for c in first_load['cases']}
    comparison = []
    for c in load['cases']:
        key = (c['devices'], c['transport'])
        base_fps = baseline_cases[key]['committed_frames_per_second']
        initial_fps = first_cases[key]['committed_frames_per_second']
        final_fps = c['committed_frames_per_second']
        difference = 100 * (final_fps / base_fps - 1)
        comparison.append(f"| {c['devices']} | {c['transport'].upper()} | {base_fps:.2f} | {initial_fps:.2f} | {final_fps:.2f} | {difference:+.1f}% |")
    comparison_text = '\n'.join(comparison)
    performance.write_text(performance.read_text(encoding='utf-8').split(perf_marker)[0].rstrip() + '\n' + perf_marker + f'''

UTC: {load['timestamp']}. Aynı yerel Docker/WSL2/PostgreSQL ortamı; [V2 ham ölçüm](verification/v2-load.json). Simulator durduruldu, yalnız ölçüm için API_RATE_LIMIT=20000 kullanıldı; sonunda 1200 geri getirildi. Ölçüm sırasında frontend/firmware build, E2E veya başka test çalıştırılmadı. Her vaka 12 producer worker, 4 tur ve her tur sonunda gerçek PostgreSQL commit doğrulaması kullanır. Fleet API ölçümü 500 pano üzerinden 10 istek/vakadır.

| Pano | Taşıma | Commit/beklenen | Frame/s | İstek/PUBACK p95 ms | Ingest başlangıcı p95 ms | Fleet API p95 ms |
|---:|---|---:|---:|---:|---:|---:|
''' + '\n'.join(rows) + f'''

**6/6 PASS, 6800 / 6800 commit**. PUBACK veritabanı commit'i değildir; ölçüm ayrıca commit sayısını bekler. Ingest metriği üretici timestamp'inden worker girişine kadardır; transaction bitişi değildir. Kısa sentetik burst; TLS/WAN/gerçek RF yoktur, host kaynakları münhasır değildir. Uzun üretim kapasitesi veya sıfır kayıp garantisi olarak kullanılmaz.

V1 karşılaştırması çalışma öncesi [baseline](verification/v2-baseline/load.json) ile yapılır. [İlk V2 ölçümü](verification/v2-load-before-history-projection.json) daha düşük ham throughput gösterdi. Risk hesabında kullanılmayan geçmiş `result/actions` ve ORM alanlarının okunması kaldırıldı; aynı 12 kaydın ölçüm/kalite/zaman/adım değerleri korunarak dar SQL projection uygulandı. Projection sonrası [ara ölçüm](verification/v2-load-before-scenario-index.json) de korundu. Gerçek PostgreSQL EXPLAIN, legacy senaryo filtresinde tüm eşleşen pano satırlarının taranıp sıralandığını gösterdi. Aynı JSON senaryo ifadesini ve timestamp sırasını kullanan, yalnız run kimliği olmayan kayıtlara ait kısmi indeks eklendi. [Önce/sonra sorgu planı](verification/v2-history-index.json), aynı sonuç içerik hash’ini, sıralamanın kalkmasını ve iki tekrar açılışta verinin korunmasını doğrular. Yukarıdaki son yük ölçümü bu indeksle yapıldı.

| Pano | Taşıma | V1 baseline frame/s | İlk V2 frame/s | Son V2 frame/s | V1'e göre fark |
|---:|---|---:|---:|---:|---:|
{comparison_text}

V1 baseline'ın ilk vakası {baseline_load['cases'][0]['metrics_before']['telemetry_rows']:,} kalıcı satırla, son V2 ölçümü {load['cases'][0]['metrics_before']['telemetry_rows']:,} satırla başladı; geçmiş silinmedi.

Bu kısa koşular host yükü, büyüyen kalıcı geçmiş ve ek V2 run/action işlemleri bakımından mutlak eşdeğer değildir; toplam hız farkı yalnız indekse atfedilmez. İndeksin sorgu planına etkisi aynı veri üzerinde ayrıca doğrulanmıştır. Negatif farklar açıkça daha düşük ham throughput demektir. Tüm vakalarda commit beklentisi karşılandı; sürekli demo kabulü ayrıca 50 frame/s yayın bütçesi ve 499 arka plan panonun ilerlemesiyle ölçüldü. Uzun süreli kapasite ayrı doğrulama gerektirir.

Sürekli 500 pano demosunda tek focus 1,5 s, 499 arka plan ≈10,115 s ve 49⅓ frame/s bütçe; ortak scheduler kapısı toplam 50 yayın/s ile sınırlı. Ayrı gerçek runtime combined **{measured['combined_critical_seconds']:.3f}s**, arc **{measured['arc_seconds']:.3f}s**, fark 10 sentetik adım ölçtü; bütün 499 arka plan pano ilerledi. Bu süreler gerçek saha arıza tahmin zamanı değildir. API ingest ortalaması kuyruk boşalmasından etkilenebilir; yayın tavanı virtual-clock scheduler testinde ayrıca doğrulanır.

SCADA V2 üç banktır: 247 + 247 + 6. PNL-500 iç port 1504 / unit 6; son Windows host TCP portu {presentation['scada_host_pnl500_port']}. Her bank aynı salt okunur haritayı kullanır. [Yapılandırma](scada/register-map.md). UI ölçek tablosu bu V2 JSON'dan SHA256 ile türetilmiştir; eski V1 tablo yukarıda korunur.

```powershell
docker compose stop simulator
docker compose -f docker-compose.yml -f tests/load/compose.load.yml up -d api scada
docker compose exec -T api python scripts/load_test.py --devices 100,250,500 --rounds 4 --transport both --output /tmp/v2-load.json
docker compose cp api:/tmp/v2-load.json docs/verification/v2-load.json
docker compose up -d api scada simulator
```

Ardından `apps/web` içinde `node scripts/project-scale-proof.mjs --input=../../docs/verification/v2-load.json --version=v2` ve web build yapılır. Sunumu `python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation` ile temiz current-run'a alın; load geçmişini silmeyin. Tarihli V1 rapor üreticisini çalıştırarak eski dosyaları ezmeyin.
''', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'python': result['python_tests']['passed'], 'container': result['container_tests']['passed'], 'frontend': 13, 'stack': 11, 'commits': 6800}))


if __name__ == '__main__':
    main()
