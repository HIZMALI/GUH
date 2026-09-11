# Gereksinim izlenebilirliği — V2

Esas kaynak `Grid Up Hackathon Proje Konusu.pdf`, s.1–5; [sayfa çözümlemesi](source-analysis.md). Belgede bulunmayan puan ağırlığı, doğruluk oranı veya ROI uydurulmadı.

| Requirement / Gereksinim | Source / Kaynak | Implementation / Uygulama | Demo evidence / Demo kanıtı | Test evidence / Test kanıtı | Limitation / Sınır |
|---|---|---|---|---|---|
| Operasyonel/çevresel veri | Proje Konusu s.1–3; MPR s.1; TVOC RevD s.21–28; Excel 152 satır | Akım/gerilim/güç/PF/frekans/THD, sıcaklık/ΔT/nem, PD, ABB; telemetry schema | Pano kanalları/köken rozeti | Replay/quality/source/decoder testleri | Excel yalnız L1 sentetik; diğerleri üretilir |
| Normal/anormal ayrımı | Proje Konusu s.1–3,5 | Açıklanabilir katkı puanı/trend/kalite; anomaly_engine | Risk katkı kartı | Risk regresyonu ve V2 API testleri | Eşikler koruma ayarı değildir |
| Kritik öncesi risk | Proje Konusu s.1–3; V2 §3–5 | Aynı run için dört durum geçişi/yapısal timeline | [Timeline](verification/v2-early-warning.png) | [Gerçek süre/lead](verification/v2-runtime.json), run testleri | Lead sentetik adım, saha öngörü dakikası değil |
| Saha-merkez aktarımı | Proje Konusu s.2–4 | Readonly MPR/TVOC, MQTT QoS1, PostgreSQL; [firmware](hardware/firmware.md) | Run→olay→alarm zinciri | [Gerçek kesinti](verification/v2-stack.json), host C++ | Fiziksel adapter implementasyonu, canlı firmware→API normalizer ve saha commissioning yok |
| Operasyon ekranı | Proje Konusu s.2–5; V2 §4,18 | Filo/filtre/şema, current/full history, alarm yaşam döngüsü | [Filo](verification/v2-fleet.png), temiz pano | V1+V2 Chromium E2E | Yerel demo; kurum bağlantısı değil |
| Otomatik aksiyon/bildirim | Proje Konusu s.2–4; V2 §6 | [Tek policy](operations/action-matrix.md), mock SMS/WhatsApp, audit | [Bildirimler](verification/v2-notifications.png), aksiyon kartı | Policy/dedupe/role ve runtime testleri | Trip/reset/gerçek SMS yok |
| Fiziksel kart/MCU | Proje Konusu s.3–4; V2 §8–9 | [PCB pin/netlist](../hardware/pcb/), güç/izolasyon, C++ çekirdek | Şema/kart dosyaları, uygulanabilirlik ekranı | 9 artefact testi, [host derleme](verification/v2-firmware-final.json) | Üretim/sertifikalı PCB ve embedded build değil |
| Kurulum/kesinti | Proje Konusu s.2–3; pano EK-II/14 s.51; V2 §10,15 | [A/B/C](installation-matrix.md), H1 sağ yardımcı TH-A | [Kurulum](verification/v2-installation.png), H1 seçimi | H1 SVG/docs/UI tutarlılık testi | Enerjili montaj talimatı değil |
| Kablosuz/tak-çalıştır | Proje Konusu s.2–3 | [Yeni çevresel sensörde kablosuz](wireless-design.md); mevcut Modbus kablolu | Yaygınlaştırma “uygun noktada kablosuz” | Tasarım/artefact kontrolü; RF saha testi yapılmadı | Metal kabin RF/pil ömrü ölçülmeli |
| Farklı sahalarda ölçek | Proje Konusu s.3–5; V2 §7,16,23 | 100/250/500, tek focus, üç SCADA bankı | Ölçüm tablosu, [PNL500](verification/v2-scada-bank500.png) | [V2 yük](verification/v2-load.json), 500 ayrı TCP unit testi | Kısa burst; üretim SLO değil |
| Maliyet sürdürülebilirliği | Proje Konusu s.2–3,5; V2 §12 | [Üç paket/boş girdili TCO](cost-benefit.md) | Yaygınlaştırma maliyet modeli | TCO boş/eksik/negatif ve hesap testleri | Teklif yokken fiyat/ROI yok |
| Yenilikçilik | Proje Konusu s.5; V2 §13 | [12 teknik fark](innovation.md), retrofit/korelasyon/kalite | Yaygınlaştırma teknik farklar | Risk/provenance/policy/SCADA bileşen testleri | Patent/benzersizlik veya saha doğruluğu iddiası yok |
| Sıcaklık/yoğun manyetik alan | Proje Konusu s.2; TEDAŞ §1.4,2.2.9(iii),3.1.2 | [Çevresel/EMC planı](hardware/environmental-emc-plan.md), aday bileşenler | Kurulum saha doğrulama sınırları | Belge/artefact kontrolü; lab testleri yapılmadı | Plan laboratuvar sonucunun yerine geçmez |

## V2 açıklarının kapanışı

| V1 açığı | V2 karşılığı | Doğrulama |
|---|---|---|
| 500 panoda seçili demo yavaştı | Tek focus 1,5 s; arka plan 49⅓ frame/s; toplam yayın tavanı 50 | Virtual-clock scheduler + gerçek 500 pano demo |
| Eski kritik grafik yeni koşuya karışıyordu | Kalıcı run/revision, pending, güncel görünüm, sayfalı geçmiş | Isolation/migration testleri, eski PostgreSQL içerik digest'i |
| Erken uyarı yalnız anlatımdı | Kalıcı event'ten state/timestamp/step ve warning→critical farkı | Yapısal timeline/API/UI |
| İlk 247 SCADA sınırı | 247+247+6; port 1502/1503/1504; aynı readonly map | Her 500 kimliğe ayrı TCP yanıtı; canlı altı sınır ve yazma reddi |
| PCB/firmware konsept düzeyindeydi | EDA bağımsız kart dosyaları + derlenen host çekirdeği | Artefact şema testleri ve host raporu; embedded ayrı NOT_RUN |
| Değer/kurulum kanıtları dağınıktı | Yaygınlaştırma, TCO, paketler, A/B/C, kaynaklı çevre planı | E2E, boş girdide fiyat üretmeme testi |

Tam sonuç [V2 kabul](acceptance.md#v2-hackathon-readiness) ve [makine özeti](verification/v2-evidence.json). V1 kayıtları tarihli kanıt olarak korunur; [değişiklik öncesi tekrar](verification/v2-baseline/summary.json) temiz Git commit'inden alınmıştır.
