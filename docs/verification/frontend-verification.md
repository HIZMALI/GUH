# Frontend Doğrulaması — V1 Referansı

11 Eylül 2026 (Europe/Istanbul), test başlangıcı **2026-09-10T23:36:13.873Z**. Bu rapor belirtilen ortamda çalıştırılan frontend kontrollerini kapsar.

## Üretim tarayıcı testi

Komut: repository `apps/web` dizininde `npm run test:e2e`.

Hedef: `http://127.0.0.1:3000`, Docker standalone Next.js frontend; yerel FastAPI, PostgreSQL, Mosquitto, gerçek simülatör ve Modbus TCP bridge. Filo 500 sanal panodur; simülatör 10 saniye etkin çevrimle çalışıyordu. Headless Chromium 153.0.8010.12, Playwright 1.63.0; desktop viewport 1440×1100, mobile 390×844.

**Sonuç: 7 başarılı, 0 başarısız, 0 skipped, 0 flaky. Süre 96.728 saniye.** Makine tarafından üretilen rapor: [frontend-e2e.json](frontend-e2e.json).

1. Gerçek API login; filo risk sıralaması ve PNL-001 araması; kaynağa dayalı pano şeması, tıklanabilir H1/P1 noktaları; 23 ölçüm ve trend yüzeyi. Browser page error yok.
2. Gerçek Modbus TCP master: bağlantı başarılı, 12 salt okunur register. Bu test DB değerlerini TCP yanıtı gibi taklit etmez.
3. Viewer senaryo düğmesi disabled; gerçek API mutasyon isteği HTTP403; logout sessionStorage bearer kaydını temizler.
4. UI'da 10 senaryo seçeneği; PNL-001 için arc_event seçimi gerçek API'ye kaydedilir. Simülatörün step8 ark olayı yaklaşık90 saniyede görülür; aktif alarm onaylanır; mock bildirim kaydı görünür. Test sonunda pano normal_operation seçimine döndürülür. Fiziksel cihaza komut gönderilmez.
5. Açıkça enjekte edilmiş HTTP502 response fixture ile frontend eski değerlerin güncel kabul edilmemesi uyarısını gösterir. Bu bir ağ-kesintisi UI sınır testidir; gerçek backend kapatılmaz.
6. Mobil menü/kaynak ekranı ve ana sayfada yatay sayfa taşması yoktur. Pano tablosu kendi içinde yatay kaydırılır.
7. Açıkça enjekte edilmiş kalite response fixture ile137% geçersiz nem sayı gibi gösterilmez; emdash ve Geçersiz veri görünür. Arc iletişim kaybı Bilinmiyor olarak görünür. G1 gateway bilgisi sensör pili yerine gateway bağlantısını gösterir.

## Build / tip / format

- Üretim derlemesi `npm run build`: PASS. Next.js16.3.4; React19.3.0; TypeScript5.9.3 strict/noUnused kontrolleri. Dört route: `/`, `/_not-found`, `/api/[...path]`, `/icon.svg`.
- `npm run typecheck`: PASS.
- `npx prettier --check src next.config.ts playwright.config.ts scripts tests/e2e package.json tsconfig.json`: PASS; son metin değişikliği için component format kontrolü ayrıca PASS.
- Dependency installation audit: 0 vulnerabilities (kurulum anındaki npm audit sonucu).

Bu kayıt V1 sürümüne ait tarihli test ortamını belgeler. Görseller o sürümün sağlık açıklaması ve grafik eksenini yansıtabilir; güncel arayüz ve tam regresyon [V2 doğrulamasında](v2-frontend-verification.md) yer alır.

## Görsel kanıtlar

Gerçek üretim container'ından alınan görüntüler; herhangi bir kullanıcı parolası veya bearer token içermez:

- [Masaüstü filo](frontend-fleet-desktop.png)
- [Pano ve izleme noktaları](frontend-panel-desktop.png)
- [Ölçümler ve trendler](frontend-trends-desktop.png)
- [Gerçek TCP master](frontend-scada-desktop.png)
- [HTTP502 UI sınırı](frontend-offline-desktop.png)
- [Mobil filo](frontend-fleet-mobile.png)

Masaüstü/mobil ekranlar görüntülenerek kontrol edildi; tablo/şema/trendler okunabilir, içerik dışarı taşmıyor. Sayfa görüntüleri uzun sayfa tam boy capture'larıdır.

Bu kayıt gerçek saha kurulumu, fiziksel MPR/ABB bağlantısı, RF doğrulaması, gerçek PD acquisition veya gerçek SMS/WhatsApp teslimi iddiası değildir. Tüm gözlemler sentetiktir.
