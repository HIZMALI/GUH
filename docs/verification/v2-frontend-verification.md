# V2 frontend doğrulaması

2026-09-11 UTC; yerel Docker üretim arayüzü `http://127.0.0.1:3000`. Mevcut V1 kanıtları değiştirilmedi.

## Sonuç ve başarısız denemenin kaydı

- DB recovery/stale projection/lock timeout düzeltmesi uygulanmış son backend üzerinde tam regresyon: **13/13 PASS**, 0 FAIL, 0 SKIP; 82,874 saniye (başlangıç 2026-09-11 01:18:03 UTC).
- İlk çalışma: 13 test, 12 PASS, 1 FAIL; 143,279 saniye. Eski yedi V1 regresyon testi ilk çalışmada geçti.
- Tek hata test seçicisindeydi: test `Alarmlar` adlı navigasyonu aradı; ürünün mevcut etiketi `Alarm merkezi`. Ürün kodu değiştirilmedi.
- Dar tekrar: düzeltilen alarm/bildirim testi ile ekran görüntüsü yakalama iyileştirmesi yapılan iki test, 3/3 PASS; 55,041 saniye.
- Toplam **13 benzersiz test PASS**; son tam koşuda hepsi yeniden geçti. İlk hata gizlenmedi; [ilk ham rapor](v2-frontend-first-run.json), [hata görüntüsü](v2-frontend-first-run-selector-failure.png), [dar tekrar ham raporu](v2-frontend-rerun.json), [son tam regresyon ham raporu](v2-frontend-final-regression.json), [birleştirilmiş özet](v2-frontend-summary.json) ayrı dosyalardır. Özet üç raporun SHA256 değerlerini ve her testin tüm denemelerini korur.
- Son koşunun altı V2 testinde `pageerror` ve `console.error`: **0**. İlk V1 testi ayrıca `pageerror` olmadığını kontrol eder. Diğer V1 testleri için toplu konsol hatası yokluğu iddia edilmez. Önceki dar tekrarın üç testindeki konsol kaydı da 0 idi.
- TypeScript kontrolü PASS; saf maliyet hesabının beş sınır testi 5/5 PASS. Üretim Next.js build Docker dağıtımında doğrulandı.

## Kanıtlanan davranış

Gerçek oturum açma, hiyerarşi/arama/risk sıralaması, 23 ölçüm/trend, alarm onayı, on senaryo seçeneği, oturum kapatma ve görüntüleyici yetkisi korunmuştur. Yerel Modbus TCP master; PNL-001/247/248/494/495/500 için 1/2/3 bankları, 1502/1503/1504 portlarını ve doğru Unit ID'leri okuyup 12 register göstermiştir.

Odaklı `combined_thermal_pd` seçimi yeni run oluşturdu. Son koşuda `PNL-001-r26` için Normal adım 0, Dikkat 19, Uyarı 21, Kritik 31; uyarı farkı **10 sentetik demo adımı** idi. Testin başlatma/izleme dahil gözlediği süre 48,912 saniyedir; bu gerçek saha erken uyarı süresi değildir. Yeni normal `PNL-001-r27` çalışmasında güncel alarm sayısı 0 iken 41 tarihsel alarm ve önceki kritik ölçümler korundu; tüm geçmiş sayfalaması çalıştı. Sayılar bu test anına aittir.

TH-A/H1 sağ yardımcı hacimdedir (`cx=439, cy=292`); P1 alt toprak/kablo bölgesinde kalır. Otomatik aksiyon açıklamaları API politikasından, Türkçe kural adları merkezi etiketlerden gelir. Bildirimlerin yerel mock olduğu, gerçek SMS/WhatsApp gönderilmediği banner, kanal kartları ve kayıt durumlarında görünür.

Yeni çalışma için ölçüm beklenirken eski risk/sağlık/ölçümler pano ve filo ekranında gizlenir; bekleyen pano risk önceliğine veya durum/sağlık ortalamasına dahil edilmez. Bu sınır açık bir cevap fixture'ı ile denenmiştir. V1 taşıma kesintisi ve geçersiz sensör testleri de kontrollü fixture kullanır. Tüm testler yerel gerçek API'de oturum açar; sentetik telemetri fiziksel saha verisi olarak sunulmaz.

Yaygınlaştırma ekranı CORE/THERMAL/ADVANCED PD, A/B/C erişim sınıfları, kaynak gösterilen ölçek tablosu ve boş başlangıçlı TCO formunu içerir. Para birimi, pano sayısı, dönem ve tüm maliyet bileşenleri kullanıcı girdisidir; eksik alan sıfır sayılmaz. Sıfır pano sayısı sonuç üretmez. Dört opsiyonel fayda alanı tamamlanmadan geri ödeme hesaplanmaz. E2E'deki `TEST` para birimi ve 155/15.500 çıktıları yalnız matematik kontrol girdileridir; teklif değildir. Mobil 390×844 görünümde sayfa taşması yoktur.

## Ekran görüntüleri ve son kontrol

- [Filo](v2-fleet.png)
- [Temiz çalışma / H1](v2-panel-clean.png)
- [Erken uyarı ve aksiyonlar](v2-early-warning.png)
- [PNL-500 SCADA bank 3](v2-scada-bank500.png)
- [Yaygınlaştırma ve ölçek](v2-scale-value.png)
- [Simüle bildirimler](v2-notifications.png)
- [Kurulum A/B/C](v2-installation.png)
- [Yeni çalışma ölçüm bekleme sınırı](v2-panel-pending.png)

Yedi görüntü görsel olarak incelendi: metin/sütun çakışması ve kesilen içerik görülmedi. Uzun teknik ekranlar tüm sayfa; filo ve bildirimler 1440×1100 görünüm olarak kaydedildi. Temiz pano görüntüsü son koşuda normal run ölçümü UI'ye geldikten sonra alındı; skor 8, sağlık 96, güncel alarm 0 ve sağ yardımcı hacimde H1 görünür. Önceki ölçüm bekleme görüntüsü ayrıca korundu. Son V2 yük tablosu ve temiz pano, 11 Eylül 2026 09:20:15 UTC'de üretim Docker build sonrası `scripts/capture-v2-final.mjs` ile tekrar kontrol edilip kaydedildi: `PNL-001-r40`, normal, risk 8, güncel alarm 0, V2 kaynak hash eşleşmesi ve console/page error 0. [Nihai salt-okunur kontrol](v2-frontend-final-smoke.json) PASS. Yedi ekran görüntüsünün son SHA256 değerleri birleştirilmiş özette yenilendi.

## Yeniden çalıştırma

Repo kökünde yerel `.env` ve çalışan Docker yığını gerekir; kimlik bilgileri rapora yazılmaz.

```powershell
cd apps/web
npm run typecheck
npm run test:unit
npm run test:e2e:v2
# Yalnız dar tekrar, ham raporu ayrı tutarak:
$env:E2E_REPORT_FILE = 'test-results-v2/rerun.json'
npm run test:e2e:v2 -- --grep='V2 focused|V2 deployment|V2 global'
# Recovery düzeltmesinden sonraki tam koşunun ayrı ham raporu:
$env:E2E_REPORT_FILE = 'test-results-v2/final-regression.json'
npm run test:e2e:v2
```

Final salt-okunur görünüm kontrolü: `node apps/web/scripts/capture-v2-final.mjs --panel=PNL-001 --version=v2`. Pano normal, yeni run ölçümü alınmış ve alarmı 0 olmalıdır; script senaryo değiştirmez. Kanıt özeti: `node apps/web/scripts/summarize-v2-e2e.mjs`.
