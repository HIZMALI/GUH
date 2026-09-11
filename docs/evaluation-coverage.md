# Değerlendirme Kriterleri Karşılığı

Kriterler, hackathon kapsamında sağlanan `Grid Up Hackathon Proje Konusu.pdf` belgesinin 1–5. sayfalarına dayanır. Kaynakta sayısal puan ağırlıkları belirtilmemiştir. Aşağıdaki tablo, her kriteri çalışan prototipin teknik karşılığı ve doğrulama kanıtıyla ilişkilendirir.

| Kriter | GridSentinel karşılığı | Teknik kanıt |
|---|---|---|
| Problemin doğru anlaşılması | Elektriksel, termal, nem, PD ve koruma olayı belirtilerinin pano bağlamında birlikte izlenmesi | [Kaynak analizi](source-analysis.md), [veri kökeni ve risk modeli](anomaly-engine/risk-model.md) |
| Anomali ve risk tespiti | Açıklanabilir katkı puanı, veri kalitesi ve kritik öncesi kalıcı durum geçişleri | [Erken uyarı](verification/v2-early-warning.png), [runtime ölçümü](verification/v2-runtime.json), run ve policy testleri |
| Uygulanabilirlik | Mevcut MPR/TVOC arayüzlerini kullanan retrofit yaklaşımı, referans kart ve erişim/kesinti planı | [PCB](../hardware/pcb/), [firmware](hardware/firmware.md), [A/B/C matrisi](installation-matrix.md) |
| Uçtan uca yaklaşım | Cihaz mesajından MQTT, kalıcı kayıt, risk, alarm ve operatör ekranına uzanan yerel akış | [Mimari](architecture.md), [servis kesintisi testleri](verification/v2-stack.json), [frontend doğrulaması](verification/v2-frontend-verification.md) |
| Entegrasyon | Kaynak MPR/TVOC okumaları ile ayrı GridSentinel SCADA çıkış haritası; 500 panoya TCP erişimi | [SCADA register haritası](scada/register-map.md), [PNL-500 kanıtı](verification/v2-scada-bank500.png), yazma reddi testleri |
| Maliyet/fayda | Kademeli paket seçimi ve açık girdilerle pano/filo TCO hesabı | [Maliyet modeli](cost-benefit.md), [son birim test sonucu](verification/final-verification.json) |
| Yenilikçilik | Mevcut cihaz, çoklu sinyal, veri kalitesi ve açıklanabilir kararın tek yerel akışta birleşmesi | [Tasarım tercihleri](innovation.md), risk, policy ve SCADA testleri |
| Ölçeklenebilirlik | 500 sanal pano, hızlandırılmış tek odak pano ve üç SCADA bankı | [100/250/500 yük ölçümü](verification/v2-load.json), [performans sınırları](performance.md) |
| Operatör deneyimi | Güncel koşu ve tüm geçmiş ayrımı, riskin nedeni, aksiyon önerisi ve alarm filtreleri | [Demo akışı](demo-walkthrough.md), [Chromium doğrulaması](verification/v2-frontend-verification.md), viewer/mobile kontrolleri |

Doğrulama kapsamı [kabul belgesinde](acceptance.md), kaynak-gereksinim ilişkisi [izlenebilirlik matrisinde](requirements-traceability.md) ayrıntılandırılır. Bütün gözlemler sentetiktir; fiziksel kart üretimi, RF/PD kalibrasyonu, gerçek kurum SCADA bağlantısı ve gerçekleşmiş saha faydası doğrulanmış değildir. Öneriler yetkili saha değerlendirmesinin yerine geçmez; koruma cihazlarının işlevi bağımsızdır.
