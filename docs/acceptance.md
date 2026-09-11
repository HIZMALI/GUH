# Doğrulama ve Kabul Kapsamı

Kayıtlar 11 Eylül 2026 tarihli yerel Docker Linux/WSL2 ortamına aittir. Kapsam; çalışan yazılım prototipi, kaynak temelli cihaz decoder'ları ve referans donanım/firmware çıktılarıdır. Gözlemler sentetiktir; fiziksel saha kabulü veya koruma sertifikasyonu değildir.

## Son doğrulama sonuçları

| Kontrol | Sonuç | Kanıt ve kapsam |
|---|---|---|
| Checkout Python testleri | 107 PASS; 0 failure/error | [Son doğrulama özeti](verification/final-verification.json); 28,161 s JUnit süresi |
| Harici kaynak hash testi | 1 PASS | On orijinal dokümanın SHA256 değeri izole alanda doğrulandı; dosyalar güncel checkout'a dahil değildir |
| Frontend birim testleri | 5/5 PASS | TCO boş/eksik/geçersiz girdi ve hesaplama sınırları |
| Üretim build ve TypeScript | PASS | Next.js üretim çıktısı ve tip kontrolü |
| Canlı stack smoke | PASS; 6 servis | [Özet](verification/final-verification.json); HTTP health ve servis durumu |
| PNL-500 TCP | PASS | Bank 3 / iç port 1504 / unit 6; API ve doğrudan host okuması |
| Normal demo filosu | 500 NORMAL / 0 offline / 0 güncel açık alarm | Aynı canlı smoke kaydı |
| Tam Chromium regresyonu | 13/13 PASS | [Ham sonuç](verification/v2-frontend-final-regression.json), [test kapsamı](verification/v2-frontend-verification.md); 91,579 s |
| Servis kesinti ve toparlanması | 11/11 PASS | [Stack raporu](verification/v2-stack.json); API, PostgreSQL ve MQTT |
| 100/250/500 HTTP ve MQTT yükü | 6/6 PASS; 6800/6800 commit | [Yük raporu](verification/v2-load.json), [ölçüm yöntemi](performance.md); kısa burst |
| C++ host çekirdeği | 7 grup / 308 kontrol PASS | [Firmware raporu](verification/v2-firmware-final.json); ESP32 hedef build değildir |
| Donanım artefaktları | 9 test PASS | [Referans kart doğrulaması](../hardware/pcb/verification.json); 31 connector pini, 199 net düğümü |

Kaynak hash testi orijinal PDF/XLSX girdilerini gerektirir; diğer 107 test bunlar olmadan çalışır. Tam 108-test host/container kayıtları, orijinallerin mevcut olduğu ortamın doğrulamasıdır: [host JUnit](verification/v2-python-tests.xml), [container JUnit](verification/v2-python-container-tests.xml). V1'e ait tarihli karşılaştırma kanıtları [baseline kaydında](verification/v2-baseline/summary.json) korunur. Farklı ortamlarda tekrarlanan aynı testler ayrı özellikler olarak sayılmaz.

## Uygulama Kabul Kapsamı

| Kabul başlığı | Doğrulanan karşılık | Teknik kanıt / sınır |
|---|---|---|
| Gereksinim kapsamı | Kaynak, uygulama, doğrulama ve sınır ilişkisi | [İzlenebilirlik](requirements-traceability.md), [değerlendirme kapsamı](evaluation-coverage.md) |
| Hızlı odak demo | Combined 48,096 s; arc 13,050 s; 499 arka plan pano ilerledi | [Runtime](verification/v2-runtime.json); hızlandırılmış sentetik zaman |
| Erken uyarı | WARNING adım 21 → CRITICAL adım 31 | Kalıcı olaylardan 10 sentetik adım; saha öngörü süresi değildir |
| Güncel koşu ve geçmiş | Yeni koşuya eski kritik ölçüm taşınmaz; geçmiş erişilebilir | Isolation/pagination/migration testleri; [237.402 eski satırın içerik koruması](verification/v2-legacy-preservation.json) |
| Aksiyon politikası | ATTENTION bildirim üretmez; WARNING iki mock kanal üretir | [Politika](operations/action-matrix.md), [canlı API/UI sayımları](verification/v2-frontend-observations.json) |
| Tam SCADA adresleme | 247 + 247 + 6 pano; 38 Modbus testi | 500 ayrı TCP unit yanıtı, altı canlı sınır, yazma/invalid/pending/stale reddi |
| Saha yaklaşımı | Referans kart, H1/TH-A konumu ve A/B/C erişim sınıfları | [Kart](../hardware/pcb/), [kurulum](installation-matrix.md), [çevresel/EMC planı](hardware/environmental-emc-plan.md) |
| Maliyet ve yenilik | Kademeli kapsam, boş girdide fiyat üretmeyen TCO ve açıklanabilir karar | [Maliyet](cost-benefit.md), [tasarım tercihleri](innovation.md) |

## Veri güvenilirliği ve hata sınırları

- Cihaz kimliği, zaman sırası, kalıcı tekilleştirme, yeniden başlatma ve run/adım idempotency kontrolleri uygulanır.
- Eksik, geçersiz, sabitlenmiş veya stale ölçüm normal veri olarak değerlendirilmez. Arc Guard ve gateway iletişim durumları ayrıdır.
- Gerçek DB kesintisinde HTTP503; toparlanmada servis erişimi ve kesinti mesajının tam bir kez commit edilmesi doğrulanmıştır.
- SCADA readiness ile bağlantı/havuz/SQL/socket/kilit/DNS sınırları regresyon kapsamındadır. Tespit edilen toparlanma hataları giderilmiş ve final kontroller başarıyla tamamlanmıştır.
- Viewer rolü, yetkisiz mutasyon reddi, alarm onayı ve mock bildirim tekilleştirmesi test edilmiştir.

SQLite expression-index reflection ve üçüncü taraf deprecation uyarıları raporlarda ayrı görünür; test failure/error olarak sayılmaz. İndeksin tekrar açılışta korunması ve legacy sonuç içeriğinin değişmemesi ayrıca doğrulanmıştır.

## Teknik sınırlar

GridSentinel izleme ve karar desteği sağlar; kesici kontrolü, TVOC reset veya koruma cihazına yazma yolu içermez. Gerçek ADM/GDZ bağlantısı, fiziksel MPR/ABB erişimi ve SMS/WhatsApp teslimi yapılmamıştır.

Referans firmware; host üzerinde test edilmiş C++ çekirdeği içerir. Fiziksel UART/BLE/Ethernet/NVM/watchdog/MQTT adapter implementasyonu ve canlı firmware verisini API'ye dönüştürecek normalizer henüz tamamlanmamıştır. ESP32 hedef build/flash **NOT_RUN**; PCB üretimi ve ERC/DRC **NOT_RUN** durumundadır.

RF kapsama, pil ömrü, kalibre PD, EMC/IP/izolasyon, gerçek saha eşikleri ve maliyet/fayda sonuçları doğrulanmamıştır. Performans tek API süreci ve kısa burst ile ölçülmüştür; uzun süreli yük, çoklu worker, yedekten dönüş ve saha commissioning ayrı kapsamdır.
