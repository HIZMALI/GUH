# GridSentinel'ın teknik yenilik yaklaşımı

Yenilik iddiası yeni bir koruma cihazı veya patentlenebilir ilk buluş iddiası değildir. GridSentinel, mevcut dağıtım ekipmanlarının verisini, ek sensörleri ve operatör iş akışını aynı açıklanabilir izleme katmanında birleştiren bir prototiptir. Kaynak problem belgesinin s.4–5 değerlendirme başlıklarına cevap verir.

| Yaklaşım | Somut karşılığı | Sınır |
|---|---|---|
| Önce retrofit | Kaynak 1600 kVA geometrisi ve mevcut MPR/TVOC arayüzleri esas alınır | Fiziksel montaj yapılmadı; yerleşim öneridir |
| Mevcut yatırımı kullanma | MPR elektriksel verileri, uygun TVOC-COM olay/tanı kayıtları | Cihaz/COM mevcudiyeti keşifte doğrulanır |
| Uygun yerde kablosuz | Yeni çevresel/yüzey sıcaklık düğümleri, yakın receiver; merkeze Ethernet | RF/pil/izolasyon doğrulanmadı; radyo zorunlu değildir |
| Çoklu sinyal ilişkisi | Yük-sıcaklık uyumsuzluğu, termal + PD katkıları | Olası neden; kesin arıza teşhisi değil |
| Açıklanabilir karar | Katkı puanı, gözlem, olası neden, öneri ve aksiyon politikası | Skor fiziksel arıza olasılığı değildir |
| Kaliteyi hesaba katma | Missing/invalid/stuck/stale, bağımsız Arc Guard iletişimi | Verisizlik normal çalışma diye gösterilmez |
| Koruma bağımsızlığı | Monitoring salt okunur; ABB ve mevcut koruma kendi işlevini sürdürür | Trip/reset/breaker çıkışı yok |
| Şirket içi SCADA entegrasyonu | Yerel MQTT/PostgreSQL ve 500 panoyu kapsayan üç TCP bankı | Gerçek ADM/GDZ üretim bağlantısı yok |
| Veri kökeni ve demo run kimliği | Kaynak L1 replay / üretilmiş kanallar; eski çalışma yeni grafiğe karışmaz | Bütün gözlemler sentetik |
| Kademeli yaygınlaştırma | CORE / THERMAL / ADVANCED PD ve teklif tabanlı TCO | Fiyat/ROI/saha tasarrufu uydurulmaz |
| Müdahaleyi görünür kılma | Her bileşene A/B/C erişim ve kesinti sınıfı | Tak-çalıştır canlı çalışma izni değildir |
| Merkezi ölçek | 100/250/500 cihaz yük testi, global pacing, hızlı tek demo paneli | Kısa yerel burst, production SLO veya soak değil |

Deterministik kurallar ve bağlamsal istatistikler bu prototip için bilinçli tercihtir. Elde yalnız sentetik örnekler varken ek bir ML modeli, saha doğruluğu iddiası için kanıt oluşturmaz. Mühendislik varsayımları ve kararın kaynak veriye kadar izlenebilirliği, risk açıklaması ve veri kökeni görünümünde yer alır.

Operasyonel karşılık: **GridSentinel alarmı, nedenini, veri güvenilirliğini ve operatöre düşen işi birlikte gösterir; mevcut koruma işlevine müdahale etmez.**

Kanıtlar: [risk modeli](anomaly-engine/risk-model.md), [mimari](architecture.md), [aksiyon matrisi](operations/action-matrix.md), [maliyet modeli](cost-benefit.md), [kabul kaydı](acceptance.md).
