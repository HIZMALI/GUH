# Kablosuz retrofit tasarımı ve doğrulama planı

Yeni sensörlerde kablolamayı azaltma hedefi vardır; mevcut MPR/ABB ölçüm ve koruma sistemlerini yeniden tasarlamak hedef değildir. Seçimler **saha deneyi bekleyen mühendislik konsepti**dir. Radyo modülü/sensör satın alınmadı, kapsama/pil ömrü ölçülmedi.

| Veri kaynağı | Seçim önerisi | Gerekçe ve kabul sınırı |
|---|---|---|
| MPR-53CS elektriksel verileri | Mevcut RS485, salt okunur | CT/VT ve ölçüm cihazı kullanılabilir; yeni kablosuz akım sensörü eklemeye gerek yok |
| ABB TVOC-2-COM | Ayrı RS485 veya onaylı mevcut master üzerinden okuma | Koruma yolu ve optik detector yapısı korunur; critical safety function radyo veya merkez sunucuya taşınmaz |
| Yeni yüzey sıcaklık / hava sıcaklık+nem | Kabin içi yakın yerel receiver'a düşük güç BLE sınıfı bağlantı öncelikli aday | Az veri; sensör değişimi kolay; model/izolasyon/pil/metal yüzey uygunluğu saha kabulünde seçilecek |
| Receiver→merkez | Yerel Ethernet / authenticated MQTT | Metal panodan bina ağına RF menzil varsayımı yapılmaz; şirket içinde kontrollü ağ |
| HFCT ham PD | 50Ω koaksiyel→uygun acquisition | MHz bantta ham PD'yi yavaş kablosuz sensör mesajı veya MCU ADC ile eşdeğer saymak yanlış |
| PD türetilmiş feature | Acquisition→gateway yerel Ethernet | Waveform yerine timestamp,quality,feature iletimine uygun; demo feature'lar sentetik |

BLE seçimi kesin ürün/standart uyumluluk beyanı değildir; saha kriterlerini karşılamazsa kablosuz ısrarı yoktur. Kabin içi alıcı metal bariyer etkisini azaltmak için sensörle aynı hacimde denenir. Dış anten, uygun RF geçişi veya kutu dışı receiver ancak IP/EMC/servis gereksinimi korunarak değerlendirilir. LoRa/sub-GHz uzak mesafe için aday olabilir; metal kabin, yerel RF tahsisi, gateway maliyeti ve enterprise policy doğrulanmadan daha güvenilir diye varsayılmaz. Wi-Fi'nin bina ağı bağımlılığı ve pil bütçesi sensör katmanı için ayrıca değerlendirileceğinden ilk konseptte kullanılmaz.

Ek birincil radyo referansı, 11 Eylül 2026 kontrolü: [Bluetooth SIG LE Primer, §6.1 ve §7.8.1](https://www.bluetooth.com/bluetooth-le-primer/), LE'nin 2.4 GHz bandını 40 kanala ayırdığını ve bağlantı için adaptive frequency hopping yaklaşımını açıklar. Normatif PHY ayrıntıları [Bluetooth Core 6.2 Radio Physical Layer](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/radio-physical-layer-specification.html) içindedir. Bu özellikler metal pano içinde yeterli kapsama, pil ömrü veya protection-grade güvenilirlik kanıtı değildir; yukarıdaki saha kabul planı hâlâ gereklidir. Bunlar yardımcı protokol referanslarıdır; verilen MPR/ABB/HFCT PDF'lerinin donanım kaynak doğruluğunu değiştirmez ve çalışma sırasında internete bağımlılık eklemez.

Tak-çalıştır; elektriksel keşif olmadan canlı pano içine montaj anlamına gelmez. Düğüme benzersiz identity atanması, authorized commissioning, hangi panel/noktaya bağlı olduğunun kaydı, eşik/kalite profili ve test mesajı sonrası sisteme alınması demektir. Termal yüzey sensörünün izolasyon ve gerilim sınıfı, pil kimyası/sıcaklık limiti, bağlantı yöntemi ve üreticinin bara üzeri montaj uygunluğu belirlenmeden canlı kısıma takılmaz. Yerleşim çoğunlukla sınıfC'dir; güvenli dış ortam düğümü sınıfA/B olabilir.

Örnek haberleşme bütçesi **varsayımı**: her panoda7 çevresel düğüm; her10s'de bir örnek, alarm adayı için daha sık raporlama. İlk mesaj ataması rastgele fazlandırılır, toplu boot aynı anda RF/MQTT yoğunluğu yaratmaz. Panoların RF hücreleri gateway başına ayrılır;500panel tek radio receiver üstüne yığılmaz. Bu trafik hedefi denenmiş RF kapasitesi değildir. API demo temposu farklı ve hızlandırılmıştır.

Pil ömrü formülü: kullanılabilir kapasite(mAh) / ortalama akım(mA). Ortalama; uyku, ölçüm, radio TX/RX, retries, self-discharge ve düşük/yüksek sıcaklık etkisini kapsamalıdır. Ürün seçimi ve ölçüm olmadığından bu projede ay/yıl sayısı taahhüt edilmez. Dashboard `battery_pct` generated_synthetic değeridir; gerçek pil telemetrisi değildir. Bakım planında pil bitmeden uyarı, tarih/seri kaydı ve güvenli değişim penceresi vardır.

Radyo katmanı doğrulama listesi: kapak kapalı/açık, en yoğun elektriksel yük çevresi, farklı sensor placement, antenna yönleri ve uygun enterferans koşullarında packet delivery, gecikme p50/p95/p99, tekrar sayısı, RSSI ve pil akımı ölçülür. Keşif hedefleri site sahibiyle belirlenir; örnek prototip acceptance hedefi30dakika boyunca en az%99 frame delivery ve95.percentile≤5s gecikme olabilir, **henüz ölçülmedi ve protection-grade hedef değildir**. Packet kaybı için timeout taze veri sanılmaz. RF uygunsuzsa uygun izole kablolu sensör veya dış receiver çözümü seçilir.

Yeni düğüm anahtarları unique olmalı; default ortak parola veya MAC adresini kimlik doğrulama sayma yok. Link authentication/encryption yeterliliği ürün bazında doğrulanır; sequence/messageID, replay rejection, sensor allowlist ve merkezi iptal listesi gateway'de korunur. Radio→gateway protokolü/firmware **konsept**, runnable demo ise synthetic simulator→authenticated MQTT yoludur; bu ikisi UI'da karıştırılmaz.
