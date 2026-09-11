# Jüri kontrol listesi

Kaynak: `Grid Up Hackathon Proje Konusu.pdf` s.1–5; resmî sayısal puan ağırlığı belirtilmemiştir. Toplu test sonucu [V2 özetinde](verification/v2-evidence.json).

| Başlık | Jüriye söylenecek cümle | Dashboard'da göster | Teknik kanıt | Test kanıtı | Aşırı iddia sınırı |
|---|---|---|---|---|---|
| PROBLEMİN DOĞRU ANLAŞILMASI | “Pano riskini elektrik, termal, nem, PD ve koruma olayı bağlamıyla görünür kılıyoruz.” | Filo → PNL-001 → köken | [Kaynak analizi](source-analysis.md), schema | Replay/quality/risk regresyonu | Sentetik veri gerçek saha ölçümü değildir |
| ANOMALİ VE RİSK TESPİTİ | “Puanın nedenini ve kritik öncesi uyarı adımını gösteriyoruz.” | Termal+PD → katkı/timeline | Rule engine, same-run trend/events | [Runtime](verification/v2-runtime.json), run testleri | Saha doğruluğu/öngörü süresi garantisi yok |
| UYGULANABİLİRLİK | “Mevcut yatırımı koruyan retrofit kart ve müdahale planı hazırladık.” | H1 sağ TH-A; Kurulum | [PCB](../hardware/pcb/), [firmware](hardware/firmware.md), [A/B/C](installation-matrix.md) | Artefact/host/H1 testleri | Kart üretilmedi; kesintisiz kurulum garantisi yok |
| UÇTAN UCA YAKLAŞIM | “Cihaz mesajı yerel MQTT'den kalıcı kayıt, alarm ve ekrana ulaşıyor.” | Run → olay → alarm → bildirim | Stable message id, PostgreSQL | [Servis kesintileri](verification/v2-stack.json), E2E | Host testi fiziksel sensör zinciri testi değil |
| ENTEGRASYON | “MPR/TVOC okumalarını ayrı GridSentinel haritasıyla SCADA'ya açıyoruz.” | PNL-500 bank 3 / port 1504 / unit 6 | [Register map](scada/register-map.md) | 500 TCP yanıtı + canlı sınırlar + yazma reddi | Kurumun resmî haritası/bağlantısı değil |
| MALİYET/FAYDA | “Üç kademe seçilir; fiyat/fayda açık girdilerle hesaplanır.” | Yaygınlaştırma TCO/paket | [Maliyet modeli](cost-benefit.md) | TCO boş/negatif/eksik sınır testleri | Teklif ve saha faydası yokken ROI yok |
| YENİLİKÇİLİK | “Mevcut cihaz, çoklu sinyal, kalite ve açıklanabilir karar tek yerel akışta birleşir.” | Yaygınlaştırma | [Yenilikçilik](innovation.md) | Risk/provenance/policy/SCADA testleri | Patent veya rakipsizlik iddiası yok |
| ÖLÇEKLENEBİLİRLİK | “500 pano çalışırken tek demo hızlanır; SCADA hepsini adresler.” | Filo 500, ölçüm tablosu | Scheduler/çoklu bank | [100/250/500 commit ölçümü](verification/v2-load.json) | Kısa burst, üretim sertifikası değil |
| OPERATÖR DENEYİ | “Güncel koşu, nedeni ve önerisi görünür; eski kanıta ayrıca erişilir.” | Run barı/geçmiş/alarm filtreleri | Current/full API, actions, audit | V1+V2 Chromium, viewer/mobile | Öneri yetkili saha değerlendirmesini ikame etmez |

Sunum öncesi 500 pano/0 offline, PNL-001 normal temiz run, PNL-500 TCP bağlantısı, mock etiketi ve köken görünür olmalı. [Sunum metni](final-demo-script.md), [çalıştırma](demo-guide.md). Geçmişi temizlemek için volume silmeyin.
