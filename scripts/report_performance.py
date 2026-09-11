"""Turn measured load JSON into a transparent Markdown performance report."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'docs/verification/load-results.json'
report=json.loads(path.read_text(encoding='utf-8'))
lines=['# Performans ve ölçek doğrulaması','',f"Ölçüm zamanı (UTC): {report['timestamp']}. Docker Linux/WSL2; Python {report['python']}. PostgreSQL kullanıldı, SQLite değil. Ham kayıt: `verification/load-results.json`.",'',
'## Ölçüm yöntemi','',
'Donanım: Intel Core i9-11900K; Docker için 16 mantıksal CPU ve 16.70 GB RAM görünür. Windows / WSL2 üzerinde çalıştırıldı. Kaynaklar yalnız bu projeye ayrılmış değildir. Ortam kaydı: `verification/environment.json`.','',
'Her test100/250/500 ayrı cihaz kimliğiyle4 periyodik tur üretir. HTTP12 eşzamanlı istek; MQTT QoS1 publisher aynı cihaz/mesaj formatını kullanır. Arka plan simulator ölçüm sırasında durdurulur. Her tur sonunda benzersiz message_id prefix ile **gerçek PostgreSQL commit sayısı** doğrulanır. Publisher PUBACK tek başına başarı sayılmaz. Her tur arasında250ms bekleme vardır; aşağıdaki throughput bu beklemeleri de içerir. SCADA bridge çalışmaya devam eder. Filo baştan500 kayda genişletildiği için API aggregation ölçümleri bütün satırlarda500 panoyu kapsar.','',
'Kısa burst testidir; uzun süreli production kapasitesi veya sahadaki paket kayıp oranı değildir. Teste özel API_RATE_LIMIT=20000/dakika; normal demo1200/dakika. Host kaynakları ve çalışan diğer işler gecikmeyi etkiler. TLS/network WAN gecikmesi yoktur.','',
'Son frontend derlemesinin yaklaşık 7 saniyelik kısmı bu ölçümün başlangıcıyla çakışmış olabilir. Derleme tamamlandıktan sonra ek tarayıcı testi veya derleme başlatılmadı. Sonuçlar kaynakları tamamen ayrılmış bir benchmark olarak sunulmaz; tüm mesajların commit sayıları ayrıca doğrulandı.','',
'| Cihaz | Taşıma | Kalıcı kayıt / beklenen | Frame/s | İstek/PUBACK p95 ms | Ingest başlangıcına kadar p95 ms | Filo API p95 ms | Son DB flush+commit ort. ms | Alarm işleme ort. ms/frame |','|---:|---|---:|---:|---:|---:|---:|---:|---:|']
for c in report['cases']:
    before,after=c['metrics_before'],c['metrics_after']
    accepted=after['accepted']-before['accepted']
    db=(after['db_write_ms_total']-before['db_write_ms_total'])/accepted if accepted else 0
    alarm=(after['alarm_processing_ms_total']-before['alarm_processing_ms_total'])/accepted if accepted else 0
    lines.append(f"| {c['devices']} | {c['transport'].upper()} | {c['committed']} / {c['expected']} | {c['committed_frames_per_second']:.2f} | {c['producer_request_or_puback_ms']['p95']:.2f} | {c['source_to_ingestion_received_ms']['p95']:.2f} | {c['fleet_api_ms']['p95']:.2f} | {db:.2f} | {alarm:.2f} |")
total=sum(c['committed'] for c in report['cases'])
expected=sum(c['expected'] for c in report['cases'])
lines += ['',f"Sonuç: {total}/{expected} mesaj kalıcı kayda ulaştı; {sum(c['passed'] for c in report['cases'])}/{len(report['cases'])} vaka PASS. Hata ayrıntıları ham JSON'dadır.",'',
'DB metriği final flush+commit süresidir; alarm yaratılırken yapılan önceki flush alarm işleme süresine dahildir. Alarm metriği normal frame denetimi ve arka plan stale bakımını da kapsar; SMS teslim gecikmesi değildir. `received_at - timestamp` worker ingestion başlangıcına kadar geçen zamanı ölçer, transaction commit zamanını değil. Throughput ise commitlerin tamamlanmasını bekler. Her API p95, vaka sonrası10 fleet isteğinin nearest-rank örneğidir; büyük örneklemli latency SLO kabulü değildir.','',
'## Sürekli demo temposu','',
'`SIMULATOR_MAX_FPS=50` ve `SIMULATOR_INTERVAL=3`: effective interval=max(3,pano_sayısı/50). Bu nedenle100 pano3s,250 pano5s,500 pano10s aralıkla raporlar. Büyük filoda3s sabit tempo zorlanarak oluşacak sınırsız gecikme gizlenmez. Bu ayar demo kapasitesine pay bırakır; her kurulumda yeniden ölçülmelidir. Farklı send cadence, retention ve donanım ile sonuçlar değişir.','',
'Tek Modbus bridge247 unit sunar.500 merkezi pano desteklemek500 ayrı Modbus unit tek bridge üzerinde var demek değildir; birden çok bridge/adres bankı gerekir. Dashboard tüm500 panoyu filtreler; liste aşamalı gösterilir.','',
'## Tekrar çalıştırma','',
'```powershell',
'docker compose stop simulator',
'docker compose -f docker-compose.yml -f tests/load/compose.load.yml up -d api scada',
'docker compose exec -T api python scripts/load_test.py --devices 100,250,500 --rounds 4 --transport both --output /tmp/gridsentinel-load.json',
'docker compose cp api:/tmp/gridsentinel-load.json docs/verification/load-results.json',
'python scripts/report_performance.py',
'docker compose up -d api scada simulator',
'```','',
'Başarısız test sonrasında da son komutla normal API limitini ve simulatorı geri getirin. Filo büyütme geçmişi silmez, expansion-only çalışır. Test geçmişi/audit korunur.','',
'## Dayanıklılık ve üretim sınırı','',
'`scripts/verify_stack.py --restarts` API yeniden başlatma, PostgreSQL erişimsizliği, kesinti sırasında MQTT mesajı, broker disconnect/reconnect ve TCP master davranışını ölçer; sonuç `verification/stack-results.json` içindedir. Unit/integration ve tarayıcı kabul matrisi `acceptance.md` içinde.','',
'Üretim için uzun süreli soak testi, disk dolması, broker power-loss,1+gün saklama büyümesi, yedekten dönüş, cihaz sertifika rotasyonu, gerçek RF/RTU saha koşulları ve yatay partitioning ayrıca gerekir. Bunlar hackathon testleriyle doğrulanmış sayılmaz.']
(ROOT/'docs/performance.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Wrote measured report for {len(report["cases"])} cases / {total} commits')
