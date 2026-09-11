# Açıklanabilir risk modeli

## Amaç ve kanıt sınırı
Model mühendislik demo kuralları ve kayan istatistikleri birleştirir. Skor, fiziksel arıza olasılığı veya sertifikalı güvenlik seviyesi değildir. Kaynak Excel yalnız152 sentetik L1 örneği içerdiğinden model doğruluğu, saha precision/recall veya %99 başarı iddiası yapılmaz. ML/Isolation Forest eklenmedi: gerçek etiketler ve temsil gücü olan veri olmadan bu ek katmanın faydası gösterilemez. Kaynaklarda olmayan eşikler açıkça demo varsayımıdır.

## Hesaplama
`services/anomaly_engine/risk.py` normatif çalışan uygulamadır. Risk8 tabanından başlar; koşullu katkıların toplamı0–100'e kırpılır. Severity NORMAL<20, ATTENTION20–44, WARNING45–79, CRITICAL>=80. İleri termal/PD birlikteliği ve bağımsız ark olayı critical üretir. Ark olayı100'e çıkar; protection komutu oluşturulmaz.

Termal55/65/80°C, nem75/85/95%, PD baseline1.8/3/5× gibi gösterim eşikleri kullanılır. Akım izleme noktası ana giriş olarak modellenir; anma referansı kaynak TEDAŞ Tablo3a'daki2312 A'dır. Bu referansın0.95/1.0/1.2 katı warning katkı seviyeleri demo varsayımıdır; protection setpoint değildir. Excel'deki600A/100mA yalnız sensör dönüşüm oranıdır, fider akım sınırı diye kullanılmaz. Faz dengesizliği, frekans ve THD katkıları API explanation'da ad/değer/puan olarak döner. Kaynak replay normal durumunu koruyacak şekilde akım eşikleri tüm152 örnek üzerinde test edilir.

En çok12 önceki kabul edilen frame üzerinden sıcaklık medyanı, EWMA(α=0.3), MAD tabanlı robust-z ve medyana göre sıcaklık değişimi hesaplanır. Yük artışı küçükken sıcaklık artması, ayrıca termal ve PD artışının birlikte olması ek kanıttır. Bu ilişki "olası gevşek bağlantı/izolasyon bozulması" açıklaması üretir; kesin teşhis değildir. İstatistik penceresi frame bazlıdır; kaynak15 dakika aralığının hızlandırıldığı demo boyunca fiziksel dakika başına eğim diye sunulmaz.

## Sağlık ve veri kalitesi
Health96 başlangıcı risk artışı ve kalite cezasıyla azalır; `100-risk` değildir. Sensör sağlık/confidence ayrıca döner. Eksik veya imkânsız ölçüm sıfırla doldurulmaz. Kalitesi iyi olmayan değer mühendislik eşiklerine kullanılmaz. Art arda13 aynı analog değer stuck şüphesi üretir; bu definitive sensör teşhisi değildir. Donmuş sensörün arızayı gizlemesini önlemek için operatöre kalite sorunu gösterilir.

Gateway silence/age, Arc Guard iletişimi, DTC ve sensör kalite sorunları ayrı görünür. Gateway offline iken health0, risk en azWARNING ve değerler son bilinen olarak işaretlenir. Haberleşme tekrar başlayıp geçerli frame gelince durum yeniden hesaplanır. Missing data nedeniyle ekipman normal kabul edilmez.

## Zaman, kimlik ve yeniden başlatma
Timestamp timezone-aware; kaynak saatleri elapsed offset ve source_row ile saklanır. Device/message_id unique DB constraint duplicate teslimatı idempotent yapar. Out-of-order/eş zamanlı eski frame, son kabul edilen durumu geri alamaz. Aynı paneli ingest eden transaction sıraya alınır; geçersiz kaynak/cihaz bağlantısı reddedilir. Risk geçmişi DB'den okunur, backend restart sonrasında korunur.

## Alarm ve bildirim
Condition, availability ve arc alarm türleri ayrı lifecycle taşır. Yeni/escalated alarm mock notification üretir. Aynı koşul her frame'de tekrar mesaj yaratmaz; onaylamak koşulu temizlemez. Koşul normale dönünce alarm resolved olur. Peak severity çözülene dek korunur. Notification kayıtları kanal/alıcı/zaman/alarm içerir ve `simulated` olarak sunulur.

Unit ve integration testler eşikleri, bütün senaryoları, kalite sınırlarını, restart/dedupe/order ve alarm onay/çözümünü denetler. Tam entegre zincirin ölçümleri `../performance.md` ve `../verification/` içinde kayıtlıdır.
