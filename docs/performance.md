# Performans ve ölçek doğrulaması

Aşağıdaki ölçüm ve eski tek-bank/pacing açıklamaları korunmuş **V1 kaydıdır**. V2 yeniden ölçümü ve tek focus/üç bank davranışı belgenin sonundadır; V1 JSON dosyasının üzerine yazılmaz.

Ölçüm zamanı (UTC): 2026-09-10T23:39:29.782595+00:00. Docker Linux/WSL2; Python 3.12.14. PostgreSQL kullanıldı, SQLite değil. Ham kayıt: `verification/load-results.json`.

## Ölçüm yöntemi

Donanım: Intel Core i9-11900K; Docker için 16 mantıksal CPU ve 16.70 GB RAM görünür. Windows / WSL2 üzerinde çalıştırıldı. Kaynaklar yalnız bu projeye ayrılmış değildir. Ortam kaydı: `verification/environment.json`.

Her test100/250/500 ayrı cihaz kimliğiyle4 periyodik tur üretir. HTTP12 eşzamanlı istek; MQTT QoS1 publisher aynı cihaz/mesaj formatını kullanır. Arka plan simulator ölçüm sırasında durdurulur. Her tur sonunda benzersiz message_id prefix ile **gerçek PostgreSQL commit sayısı** doğrulanır. Publisher PUBACK tek başına başarı sayılmaz. Her tur arasında250ms bekleme vardır; aşağıdaki throughput bu beklemeleri de içerir. SCADA bridge çalışmaya devam eder. Filo baştan500 kayda genişletildiği için API aggregation ölçümleri bütün satırlarda500 panoyu kapsar.

Kısa burst testidir; uzun süreli production kapasitesi veya sahadaki paket kayıp oranı değildir. Teste özel API_RATE_LIMIT=20000/dakika; normal demo1200/dakika. Host kaynakları ve çalışan diğer işler gecikmeyi etkiler. TLS/network WAN gecikmesi yoktur.

Son frontend derlemesinin yaklaşık 7 saniyelik kısmı bu ölçümün başlangıcıyla çakışmış olabilir. Derleme tamamlandıktan sonra ek tarayıcı testi veya derleme başlatılmadı. Sonuçlar kaynakları tamamen ayrılmış bir benchmark olarak sunulmaz; tüm mesajların commit sayıları ayrıca doğrulandı.

| Cihaz | Taşıma | Kalıcı kayıt / beklenen | Frame/s | İstek/PUBACK p95 ms | Ingest başlangıcına kadar p95 ms | Filo API p95 ms | Son DB flush+commit ort. ms | Alarm işleme ort. ms/frame |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 100 | HTTP | 400 / 400 | 81.96 | 276.93 | 14.21 | 375.34 | 2.80 | 0.95 |
| 100 | MQTT | 400 / 400 | 95.41 | 4.90 | 752.13 | 343.23 | 2.26 | 0.64 |
| 250 | HTTP | 1000 / 1000 | 79.95 | 298.76 | 8.02 | 328.14 | 3.10 | 1.10 |
| 250 | MQTT | 1000 / 1000 | 101.74 | 3.63 | 2030.69 | 343.93 | 2.63 | 1.03 |
| 500 | HTTP | 2000 / 2000 | 97.68 | 251.71 | 4.40 | 318.53 | 2.76 | 1.00 |
| 500 | MQTT | 2000 / 2000 | 115.40 | 3.72 | 3739.56 | 317.50 | 2.60 | 0.93 |

Sonuç: 6800/6800 mesaj kalıcı kayda ulaştı; 6/6 vaka PASS. Hata ayrıntıları ham JSON'dadır.

DB metriği final flush+commit süresidir; alarm yaratılırken yapılan önceki flush alarm işleme süresine dahildir. Alarm metriği normal frame denetimi ve arka plan stale bakımını da kapsar; SMS teslim gecikmesi değildir. `received_at - timestamp` worker ingestion başlangıcına kadar geçen zamanı ölçer, transaction commit zamanını değil. Throughput ise commitlerin tamamlanmasını bekler. Her API p95, vaka sonrası10 fleet isteğinin nearest-rank örneğidir; büyük örneklemli latency SLO kabulü değildir.

## Sürekli demo temposu

`SIMULATOR_MAX_FPS=50` ve `SIMULATOR_INTERVAL=3`: effective interval=max(3,pano_sayısı/50). Bu nedenle100 pano3s,250 pano5s,500 pano10s aralıkla raporlar. Büyük filoda3s sabit tempo zorlanarak oluşacak sınırsız gecikme gizlenmez. Bu ayar demo kapasitesine pay bırakır; her kurulumda yeniden ölçülmelidir. Farklı send cadence, retention ve donanım ile sonuçlar değişir.

Tek Modbus bridge247 unit sunar.500 merkezi pano desteklemek500 ayrı Modbus unit tek bridge üzerinde var demek değildir; birden çok bridge/adres bankı gerekir. Dashboard tüm500 panoyu filtreler; liste aşamalı gösterilir.

## Tekrar çalıştırma

```powershell
docker compose stop simulator
docker compose -f docker-compose.yml -f tests/load/compose.load.yml up -d api scada
docker compose exec -T api python scripts/load_test.py --devices 100,250,500 --rounds 4 --transport both --output /tmp/gridsentinel-load.json
docker compose cp api:/tmp/gridsentinel-load.json docs/verification/load-results.json
python scripts/report_performance.py
docker compose up -d api scada simulator
```

Başarısız test sonrasında da son komutla normal API limitini ve simulatorı geri getirin. Filo büyütme geçmişi silmez, expansion-only çalışır. Test geçmişi/audit korunur.

## Dayanıklılık ve üretim sınırı

`scripts/verify_stack.py --restarts` API yeniden başlatma, PostgreSQL erişimsizliği, kesinti sırasında MQTT mesajı, broker disconnect/reconnect ve TCP master davranışını ölçer; sonuç `verification/stack-results.json` içindedir. Unit/integration ve tarayıcı kabul matrisi `acceptance.md` içinde.

Üretim için uzun süreli soak testi, disk dolması, broker power-loss,1+gün saklama büyümesi, yedekten dönüş, cihaz sertifika rotasyonu, gerçek RF/RTU saha koşulları ve yatay partitioning ayrıca gerekir. Bunlar hackathon testleriyle doğrulanmış sayılmaz.

## V2 yeniden ölçümü


UTC: 2026-09-11T09:15:15.457414+00:00. Aynı yerel Docker/WSL2/PostgreSQL ortamı; [V2 ham ölçüm](verification/v2-load.json). Simulator durduruldu, yalnız ölçüm için API_RATE_LIMIT=20000 kullanıldı; sonunda 1200 geri getirildi. Ölçüm sırasında frontend/firmware build, E2E veya başka test çalıştırılmadı. Her vaka 12 producer worker, 4 tur ve her tur sonunda gerçek PostgreSQL commit doğrulaması kullanır. Fleet API ölçümü 500 pano üzerinden 10 istek/vakadır.

| Pano | Taşıma | Commit/beklenen | Frame/s | İstek/PUBACK p95 ms | Ingest başlangıcı p95 ms | Fleet API p95 ms |
|---:|---|---:|---:|---:|---:|---:|
| 100 | HTTP | 400/400 | 65.93 | 334.63 | 14.53 | 475.58 |
| 100 | MQTT | 400/400 | 59.30 | 5.39 | 1859.59 | 525.21 |
| 250 | HTTP | 1000/1000 | 77.63 | 343.19 | 11.37 | 526.17 |
| 250 | MQTT | 1000/1000 | 96.65 | 3.75 | 2075.50 | 482.59 |
| 500 | HTTP | 2000/2000 | 89.44 | 292.30 | 4.55 | 395.98 |
| 500 | MQTT | 2000/2000 | 111.95 | 3.75 | 3801.45 | 384.12 |

**6/6 PASS, 6800 / 6800 commit**. PUBACK veritabanı commit'i değildir; ölçüm ayrıca commit sayısını bekler. Ingest metriği üretici timestamp'inden worker girişine kadardır; transaction bitişi değildir. Kısa sentetik burst; TLS/WAN/gerçek RF yoktur, host kaynakları münhasır değildir. Uzun üretim kapasitesi veya sıfır kayıp garantisi olarak kullanılmaz.

V1 karşılaştırması çalışma öncesi [baseline](verification/v2-baseline/load.json) ile yapılır. [İlk V2 ölçümü](verification/v2-load-before-history-projection.json) daha düşük ham throughput gösterdi. Risk hesabında kullanılmayan geçmiş `result/actions` ve ORM alanlarının okunması kaldırıldı; aynı 12 kaydın ölçüm/kalite/zaman/adım değerleri korunarak dar SQL projection uygulandı. Projection sonrası [ara ölçüm](verification/v2-load-before-scenario-index.json) de korundu. Gerçek PostgreSQL EXPLAIN, legacy senaryo filtresinde tüm eşleşen pano satırlarının taranıp sıralandığını gösterdi. Aynı JSON senaryo ifadesini ve timestamp sırasını kullanan, yalnız run kimliği olmayan kayıtlara ait kısmi indeks eklendi. [Önce/sonra sorgu planı](verification/v2-history-index.json), aynı sonuç içerik hash’ini, sıralamanın kalkmasını ve iki tekrar açılışta verinin korunmasını doğrular. Yukarıdaki son yük ölçümü bu indeksle yapıldı.

| Pano | Taşıma | V1 baseline frame/s | İlk V2 frame/s | Son V2 frame/s | V1'e göre fark |
|---:|---|---:|---:|---:|---:|
| 100 | HTTP | 86.12 | 50.72 | 65.93 | -23.4% |
| 100 | MQTT | 68.86 | 55.63 | 59.30 | -13.9% |
| 250 | HTTP | 89.66 | 63.01 | 77.63 | -13.4% |
| 250 | MQTT | 95.55 | 71.55 | 96.65 | +1.2% |
| 500 | HTTP | 94.09 | 71.29 | 89.44 | -4.9% |
| 500 | MQTT | 101.40 | 84.75 | 111.95 | +10.4% |

V1 baseline'ın ilk vakası 175,602 kalıcı satırla, son V2 ölçümü 709,976 satırla başladı; geçmiş silinmedi.

Bu kısa koşular host yükü, büyüyen kalıcı geçmiş ve ek V2 run/action işlemleri bakımından mutlak eşdeğer değildir; toplam hız farkı yalnız indekse atfedilmez. İndeksin sorgu planına etkisi aynı veri üzerinde ayrıca doğrulanmıştır. Negatif farklar açıkça daha düşük ham throughput demektir. Tüm vakalarda commit beklentisi karşılandı; sürekli demo kabulü ayrıca 50 frame/s yayın bütçesi ve 499 arka plan panonun ilerlemesiyle ölçüldü. Uzun süreli kapasite ayrı doğrulama gerektirir.

Sürekli 500 pano demosunda tek focus 1,5 s, 499 arka plan ≈10,115 s ve 49⅓ frame/s bütçe; ortak scheduler kapısı toplam 50 yayın/s ile sınırlı. Ayrı gerçek runtime combined **48.096s**, arc **13.050s**, fark 10 sentetik adım ölçtü; bütün 499 arka plan pano ilerledi. Bu süreler gerçek saha arıza tahmin zamanı değildir. API ingest ortalaması kuyruk boşalmasından etkilenebilir; yayın tavanı virtual-clock scheduler testinde ayrıca doğrulanır.

SCADA V2 üç banktır: 247 + 247 + 6. PNL-500 iç port 1504 / unit 6; son Windows host TCP portu 11504. Her bank aynı salt okunur haritayı kullanır. [Yapılandırma](scada/register-map.md). UI ölçek tablosu bu V2 JSON'dan SHA256 ile türetilmiştir; eski V1 tablo yukarıda korunur.

```powershell
docker compose stop simulator
docker compose -f docker-compose.yml -f tests/load/compose.load.yml up -d api scada
docker compose exec -T api python scripts/load_test.py --devices 100,250,500 --rounds 4 --transport both --output /tmp/v2-load.json
docker compose cp api:/tmp/v2-load.json docs/verification/v2-load.json
docker compose up -d api scada simulator
```

Ardından `apps/web` içinde `node scripts/project-scale-proof.mjs --input=../../docs/verification/v2-load.json --version=v2` ve web build yapılır. Sunumu `python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation` ile temiz current-run'a alın; load geçmişini silmeyin. Tarihli V1 rapor üreticisini çalıştırarak eski dosyaları ezmeyin.
