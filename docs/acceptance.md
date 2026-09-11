# GridSentinel kabul kaydı

11 Eylül 2026, Europe/Istanbul. Çalışan ortam yerel Docker Desktop Linux/WSL2; gözlemlerin tamamı sentetik. Sağlanan dokuz PDF ve Excel korunmuştur. Bu kayıt yazılım prototipini ve mühendislik konseptini kapsar; saha devreye alma veya koruma sertifikasyonu değildir.

## Gerçek doğrulama sonuçları

| Kontrol | Sonuç | Kanıt |
|---|---|---|
| Python, tüm testler, host Python 3.14 | **62 PASS**, 12.65 s | [JUnit](verification/python-tests.xml) |
| Aynı testler, uygulama container'ı Python 3.12.14 | **61 PASS, 1 SKIP**, 5.62 s | [Container JUnit](verification/python-container-tests.xml) |
| Production Chromium E2E | **7 PASS**, 96.728 s | [E2E JSON](verification/frontend-e2e.json), [kapsam ve görseller](verification/frontend-verification.md) |
| Gerçek Docker / API / PostgreSQL / MQTT / TCP kontrolleri | **11 PASS** | [Kesinti ve servis kaydı](verification/stack-results.json) |
| 100 / 250 / 500 cihaz, HTTP ve MQTT, dört tur | **6 PASS, 6800 / 6800 commit** | [Ham ölçüm](verification/load-results.json), [performans raporu](performance.md) |
| Next.js production Docker build | PASS | [Frontend doğrulama](verification/frontend-verification.md) |
| Son image üzerinde sağlık açıklaması ve risk ekseni | PASS; eksen 0 / 50 / 100, browser hatası yok | [Son tarayıcı kontrolü](verification/frontend-final-smoke.json) |
| Teslim anı çalışan demo | 500 pano bağlı, PostgreSQL/MQTT hazır, 12 TCP register okunuyor | [Son çalışma durumu](verification/final-runtime.json) |

Container'daki tek skip, asıl kaynak PDF/XLSX dosyalarının runtime image'a bilinçli olarak alınmaması nedeniyle kaynak hash kontrolüdür. Aynı kontrol host üzerinde geçti; skip bir PASS olarak sayılmadı. Container testindeki AnyIO deprecation uyarısı üçüncü taraf Starlette TestClient'tan gelir. Python ve container sayıları aynı testlerin iki ortamda çalıştırılmasıdır; ayrı özellik sayıları değildir.

İlk toplu host çalışmasında bir sıralama testi başarısızdı: `now - 1s` ile oluşturulan mesaj, yavaş test yeniden başlatmasında önce kabul edilen mesajdan daha yeni kalabiliyordu. Fixture, kabul edilen mesajın timestamp'inden bir saniye çıkaracak şekilde düzeltildi; ürünün sıralama kuralı gevşetilmedi. [İlk çalışmanın kaydı](verification/python-tests-first-run.xml) korunmuştur. Ardından yukarıdaki host ve container testleri geçti.

## Definition of Done eşlemesi

| No | Kullanıcının kabul ölçütü | Karşılığı ve doğrulama |
|---:|---|---|
| 1 | Docker Compose ile şirket içinde çalışma | `scripts/bootstrap.py`, `docker compose up -d --build`; altı yerel servis çalıştı. |
| 2 | Frontend açılıyor | Production Next.js, gerçek backend ile 7 Chromium E2E. |
| 3 | Backend health başarılı | `/health`: PostgreSQL bağlı; DB kesintisinde HTTP503, toparlanınca HTTP200. |
| 4 | PostgreSQL çalışıyor | Telemetri/risk/alarm/audit kalıcı kayıtları; kesintiden sonra veri korunması. |
| 5 | MQTT çalışıyor | Kimlik doğrulamalı Mosquitto, gerçek QoS1 aktarım ve broker reconnect testi. |
| 6 | Simulator telemetry gönderiyor | 500 sanal pano, MQTT; etkin yayın aralığı 10 s. İlk kurulum varsayılanı 100 pano / 3 s. |
| 7 | MPR-53CS haritası uygulanmış | `services/modbus/devices/mpr53cs.py`; kaynak adres, ölçek, tip, word order ve timeout testleri. |
| 8 | TVOC-2 haritası uygulanmış | `services/modbus/devices/tvoc2.py`; firmware, sentinel, dedektör/relay/state ve timestamp testleri. |
| 9 | Sentetik senaryolar çalışıyor | On senaryonun tamamı beklenen duruma ulaşır; replay 152 kaynak L1 değerini korur. |
| 10 | Gerçek zamanlı risk skoru | MQTT → ingestion → açıklanabilir kurallar/trend → PostgreSQL → UI akışı. |
| 11 | Alarm engine | Yeni/escalated/onaylı/resolved yaşam döngüsü; tekrar bildirim engeli test edildi. |
| 12 | Bildirim demo | Kanal, alıcı, zaman, alarm ve `simulated` durumu; ark E2E içinde görünür. |
| 13 | SCADA Modbus TCP | Ayrı bridge ve gerçek TCP master; 12 register, geçersiz adres ve yazma reddi. |
| 14 | 1600 kVA pano ekranı | Kaynak geometriye dayalı, tıklanabilir şema; masaüstü görsel QA ve E2E. |
| 15 | Normal → Attention → Warning → Critical | `combined_thermal_pd` bütün durumlara ulaşır; test ve `data/scenarios/combined_thermal_pd.json` zaman çizelgesi. |
| 16 | Ayrı ark olayı | UI'dan senaryo seçimi, simulator step8, dedektör/trip kaydı, alarm onayı ve mock bildirim gerçek servislerle doğrulandı. |
| 17 | En az 100 modül yük testi | 100, 250 ve 500 ayrı kimlik; HTTP/MQTT, commit doğrulamalı altı vaka. |
| 18 | Temel testler PASS | Yukarıdaki kayıtlar; tek kaynak-hash skip'i host üzerinde karşılandı. |
| 19 | Public cloud bağımlılığı yok | Yerel PostgreSQL/MQTT/API/UI; runtime harici servis/font/CDN çağrısı gerektirmez. |
| 20 | README ile kurulum | Tek komut ve ayrı bootstrap/build/up adımları, rastgele `.env`, Docker/port gereksinimleri belgeli. |
| 21 | Kesinti gereksinimleri açık | [A/B/C kurulum matrisi](installation-matrix.md), erişim koşulları ve daha az müdahaleli alternatifler. |
| 22 | Kablosuz/tak-çalıştır yaklaşımı belgeli | [Kablosuz tasarım](wireless-design.md); yeni çevresel sensörler, mevcut Modbus cihazları ve PD acquisition ayrılmıştır. |
| 23 | Veri kökeni açık | L1 organizer replay; diğer kanallar generated synthetic; API'de kanal kökeni/kalite, UI'da sentetik işaretleri. |
| 24 | Yanıltıcı saha/SCADA iddiası yok | Koruma sınırı, önerilen montaj ve gerçek yerel demo TCP ile fiziksel saha ayrımı UI/dokümanlarda belirtilir. |

## İstenen hata sınırları

- Modbus timeout/offline, hatalı register/unit, parçalı MBAP, read-only sınırı: `tests/modbus/`.
- Duplicate ve out-of-order telemetri, yeniden başlatma sonrası indeks/idempotency, yetkisiz cihaz: `tests/integration/test_api_backend.py`.
- Missing, stuck, impossible measurement, gateway stale ve bağımsız Arc Guard iletişimi: Python testleri; geçersiz nem/Arc UI gösterimi ayrıca açık response fixture ile sınandı.
- API restart sonrası son pano zamanının korunması, gerçek PostgreSQL kesintisi, kesinti sırasında gönderilen bir QoS1 mesajının tam bir kez commit edilmesi, gerçek broker disconnect/reconnect: `scripts/verify_stack.py --restarts`.
- API502 UI denemesi tarayıcı response fixture'ıdır; gerçek servis restart testlerinden ayrı tutulur. Gerçek SMS/WhatsApp gönderilmedi.

## Kullanım ve kapsam sınırları

Tek komut: `python scripts/run_demo.py --scenario combined_thermal_pd`. Teslim öncesi bu komut build dahil başarıyla yeniden çalıştırıldı, PNL-001 için birleşik senaryo seçildi ve altı servis çalışır bırakıldı. Ölçüme özel API limiti kaldırıldı; normal 1200 istek/dakika değeri container içinde doğrulandı. Giriş bilgileri özel `.env` dosyasındadır. Tekrar çalıştırılabilir komutlar [kurulum](install-guide.md), [demo](demo-guide.md) ve [performans](performance.md) belgelerinde bulunur. Bu makinede bootstrap, image build ve Compose başlangıcı doğrulandı; ayrı temiz bir makinede ikinci kurulum yapılmadı.

Fiziksel edge firmware/spool, native seri RTU, acquisition elektroniği ve PCB yalnız belgelenmiş konsept veya sonraki saha entegrasyonu sınırıdır. Çalışan cihaz sürücüsü arayüzü salt okunur TCP→RTU gateway üzerinden poll/decode yapabilir; gerçek saha donanımıyla denenmedi. Word order, RF kapsama, pil ömrü, eşikler, izolasyon/EMC/IP uygunluğu ve kalibre PD ölçümü doğrulanmış sayılmaz.

Merkez 500 pano destekler; bir Modbus bridge ilk 247 unit'i sunar. Daha büyük SCADA adreslemesi için çoklu bridge gerekir. Yük testi kısa burst'tür; uzun süreli üretim kapasitesi veya sıfır kayıp garantisi değildir. TLS/mTLS, saha commissioning, yedekten dönüş ve uzun soak testleri üretim uyarlamasında ayrıca gerekir. Bunlar hackathon kapsamında gerçekmiş gibi sunulmamıştır.
