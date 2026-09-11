# V2 frontend doğrulaması

2026-09-11 UTC; yerel Docker üretim arayüzü `http://127.0.0.1:3000`. Mevcut V1 kanıtları değiştirilmedi.

## Sonuç ve başarısız denemenin kaydı

- Fleet current-run alarm sayımı ve ATTENTION bildirim politikası düzeltilmiş backend üzerinde tam regresyon: **13/13 PASS**, 0 FAIL, 0 SKIP; 91,579 saniye (başlangıç 2026-09-11 12:31:19 UTC). Önceki 82,874 saniyelik tam koşu [ayrı korundu](v2-frontend-final-regression-before-final-hardening.json).
- İlk çalışma: 13 test, 12 PASS, 1 FAIL; 143,279 saniye. Eski yedi V1 regresyon testi ilk çalışmada geçti.
- Tek hata test seçicisindeydi: test `Alarmlar` adlı navigasyonu aradı; ürünün mevcut etiketi `Alarm merkezi`. Ürün kodu değiştirilmedi.
- Dar tekrar: düzeltilen alarm/bildirim testi ile ekran görüntüsü yakalama iyileştirmesi yapılan iki test, 3/3 PASS; 55,041 saniye.
- Toplam **13 benzersiz test PASS**; son tam koşuda hepsi yeniden geçti. İlk hata gizlenmedi; [ilk ham rapor](v2-frontend-first-run.json), [hata görüntüsü](v2-frontend-first-run-selector-failure.png), [dar tekrar ham raporu](v2-frontend-rerun.json), [son tam regresyon ham raporu](v2-frontend-final-regression.json), [birleştirilmiş özet](v2-frontend-summary.json) ayrı dosyalardır. Özet önceki tam koşu dahil dört raporun SHA256 değerlerini ve her testin denemelerini korur.
- Son koşunun altı V2 testinde `pageerror` ve `console.error`: **0**. İlk V1 testi ayrıca `pageerror` olmadığını kontrol eder. Diğer V1 testleri için toplu konsol hatası yokluğu iddia edilmez. Önceki dar tekrarın üç testindeki konsol kaydı da 0 idi.
- TypeScript kontrolü PASS; saf maliyet hesabının beş sınır testi 5/5 PASS. Üretim Next.js build Docker dağıtımında doğrulandı.

## Kanıtlanan davranış

Gerçek oturum açma, hiyerarşi/arama/risk sıralaması, 23 ölçüm/trend, alarm onayı, on senaryo seçeneği, oturum kapatma ve görüntüleyici yetkisi korunmuştur. Yerel Modbus TCP master; PNL-001/247/248/494/495/500 için 1/2/3 bankları, 1502/1503/1504 portlarını ve doğru Unit ID'leri okuyup 12 register göstermiştir.

Odaklı `combined_thermal_pd` seçimi yeni run oluşturdu. Son koşuda `PNL-001-r43` için Normal adım 0, Dikkat 19, Uyarı 21, Kritik 31; uyarı farkı **10 sentetik demo adımı** idi. Testin başlatma/izleme ve policy ekran yakalama dahil gözlediği süre 50,864 saniyedir; bu gerçek saha erken uyarı süresi değildir. Yeni normal `PNL-001-r44` çalışmasında güncel alarm sayısı 0 iken 63 tarihsel alarm ve önceki kritik ölçümler korundu; tüm geçmiş sayfalaması çalıştı. Sayılar bu test anına aittir.

Policy sürüm 2 için gerçek çalışan API'de ATTENTION adım 19: **0 mock bildirim**, kalıcı alarm var; WARNING adım 21: **2 simulated kayıt**, `sms_mock` ve `whatsapp_mock`, kalıcı alarm var. UI aksiyon kartı ATTENTION için iki kanalı göstermez; WARNING için ikisini gösterir. ATTENTION aralığı mevcut dört saniyelik ekran yenilemesinden kısa olduğu için bu iki görüntü, gerçek API yanıtı yalnız tarayıcı çiziminde sabitlenerek kaydedildi; backend ve simulator ilerlemeye devam etti. Bildirim sayıları canlı API'den alındı; veri üretilmiş bir response fixture'ı değildir. [Zaman/adım ve sayımlar](v2-frontend-observations.json).

Python regresyonunda mevcut 106 teste iki test eklendi: pano/run eşleşmesi ve active/acknowledged sınırı ile ATTENTION alarm/event/SCADA → WARNING bildirim yükselmesi. Yerel ve üretim container ortamlarında **108/108 PASS**. İlk dar kontrolde eski COMMUNICATION_LOSS bildirim beklentisi yeni politikayla çelişti; beklenti kullanılabilirlik aksiyonlarına göre güncellendi, ark olayının acil bildirim üstünlüğü korundu ve tam koşular geçti.

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
- [ATTENTION: bildirim kanalı yok](v2-attention-policy.png)
- [WARNING: iki mock kanal](v2-warning-policy.png)

Final hardening sırasında ATTENTION/WARNING, normal filo ve temiz pano görüntüleri görsel olarak incelendi; kesilen veya çakışan içerik görülmedi. Yeni policy ekranları ve filo tüm sayfa kaydedildi. Son salt-okunur kontrol 11 Eylül 2026 12:37:43 UTC: `PNL-001-r45`, normal, risk 8, güncel alarm 0; filo **500 NORMAL / 0 offline / 0 open_alarms**. UI metrikleri ve API yanıtı birlikte doğrulandı. Yaygınlaştırma tablosunun yeni yük raporu SHA256 değeri üretim build içinde eşleşti, console/page error 0. [Nihai kontrol](v2-frontend-final-smoke.json) PASS; dokuz ekran görüntüsünün son hash değerleri [özette](v2-frontend-summary.json).

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
# Final hardening tam koşusunun ayrı ham raporu:
$env:E2E_REPORT_FILE = 'test-results-v2/final-hardening.json'
npm run test:e2e:v2
```

Final salt-okunur görünüm kontrolü: `node apps/web/scripts/capture-v2-final.mjs --panel=PNL-001 --version=v2`. Filo 500 NORMAL / 0 offline / 0 açık alarm; pano normal, yeni run ölçümü alınmış ve alarmı 0 olmalıdır; script senaryo değiştirmez. Kanıt özeti: `node apps/web/scripts/summarize-v2-e2e.mjs`.
