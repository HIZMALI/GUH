# GridSentinel Web

Yerel Next.js / TypeScript operasyon arayüzü. Uygulama sahte canlı veri üretmez; tüm çalışma verileri FastAPI'den gelir. `/api/*` istekleri aynı-origin route handler üzerinden `API_INTERNAL_URL` adresine gider. Varsayılan `http://127.0.0.1:8000`; Compose değeri `http://api:8000`.

## Çalıştırma

Repository kökünden Windows PowerShell veya Linux terminalinde:

```text
cd apps/web
npm ci
npm run dev -- --hostname 127.0.0.1
```

UI: `http://127.0.0.1:3000`. Önce root kurulum komutuyla backend ve yerel kullanıcıları oluşturun. Login parolaları `.env` dosyasından gelir; frontend'de varsayılan parola yoktur. Başka bir yerel API kullanılacaksa `API_INTERNAL_URL` ortam değişkenini ayarlayın.

```text
npm run build
npm run typecheck
```

Docker build context `apps/web` dizinidir. Standalone image, root Compose üzerinden başlatılır. Next telemetry launcher ve Docker'da kapalıdır. Fontlar işletim sistemi fontlarıdır; remote font, CDN, cloud runtime veya hosted frontend servisi gerekmez.

## Tarayıcı testleri

Gerçek backend + PostgreSQL + MQTT + simülatör + Modbus bridge çalışırken:

```text
npx playwright install chromium
npm run test:e2e
```

Testler `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `VIEWER_PASSWORD` ortam değişkenlerini veya repository kökündeki ignored `.env` dosyasını okur; kimlik bilgilerini çıktılamaz. `E2E_BASE_URL` varsayılanı `http://127.0.0.1:3000`.

Filo, kaynak çizim şeması, trendler, gerçek TCP register okuması, viewer yetki sınırı ve logout gerçek servislere karşı denenir. Ağ kesintisi ile invalid nem / Arc bağlantı kaybı testleri açıkça belirtilmiş tarayıcı response fixture'larıdır. Bu fixture'lar uygulamanın demo verisi değildir. Senaryo testi PNL-001 üzerinde `arc_event` seçer, gerçek simülatör olayını bekler, alarmı onaylar, simüle bildirimleri kontrol eder ve panoyu `normal_operation` seçimine döndürür. 500 pano pacing 80–90 sn sürebilir; test zaman sınırı 150 sn.

JSON rapor ve masaüstü/mobil ekran görüntüleri Git dışındaki `test-results/` dizinine yazılır. Sonuçlar sürüm ve ortam bilgileriyle [frontend doğrulamasında](../../docs/verification/v2-frontend-verification.md) belgelenir.

## Operatör yüzeyleri

- Filo özeti; bölge → istasyon → trafo filtresi, arama, risk/sağlık sıralaması ve kademeli satır gösterimi.
- TEDAŞ EK-II/14 basılı s.51 geometrisine dayalı tıklanabilir pano şeması; ek monitoring noktaları açıkça öneridir.
- 23 elektriksel/termal/çevresel/PD ölçüm; UTC zaman serileri. Invalid, missing, stuck ve stale değerler sayı gibi gösterilmez; eksik trend segmentleri birleştirilmez.
- Alarm onayı, olay geçmişi, 10 sentetik senaryo seçimi, mock bildirim günlüğü, gerçek read-only TCP master ve kaynak/mimari açıklaması.
- Auth bearer token yalnızca sessionStorage'dadır; viewer arayüzü mutasyonları kapatır, nihai yetki backend'de doğrulanır. Alarm onayı koruma cihazına yazma değildir.

Donanım ölçülmüş/kurulmuş gibi gösterilmez. PD genlikleri a.u.; mühendislik eşikleri demo varsayımlarıdır. Uygulama koruma rölesi değildir.
