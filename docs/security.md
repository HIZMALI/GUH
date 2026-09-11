# Güvenlik sınırları ve uygulama

## Çalışan korumalar
Yerel bootstrap her kurulum için rastgele `.env` sırları üretir; dosya Git ve Docker build context dışında tutulur. Kullanıcı parolaları hash'lenir. API bearer kimlik doğrulama, viewer/operator/admin rolleri, cihaz kimlik doğrulama, audit, doğrulanmış JSON ve istek sınırları uygular. Operatör alarm onaylayabilir ve demo senaryosu seçebilir; viewer salt okur. Servis token'ı ayrı rol taşır. Detaylar ve sınır testleri backend testlerinde doğrulanır.

Mosquitto anonim bağlantıyı reddeder, parola dosyası bootstrap ortamından hash'lenerek oluşturulur. Demo tek publisher hesabı yalnız `gridsentinel/#` topic ağacına erişebilir. Her mesajın ayrıca cihaz kimliğine bağlı anahtarı vardır. Üretimde her gateway için ayrı broker hesabı/sertifika ve topic ACL gerekir; demo ortak broker hesabı bu ayrımı tek başına sağlamaz.

Compose özel bridge ağı kullanır. UI3000, API8000, MQTT1883 ve Modbus1502 yalnız127.0.0.1'e yayınlanır. PostgreSQL host'a açılmaz. Python servisleri root olmayan kullanıcı, tüm Linux capability'leri kaldırılmış ve no-new-privileges ile çalışır. Runtime harici font/CDN/API kullanmaz. Ağ internet çıkışını tek başına engellemez; air-gap/firewall politikası host üzerinde uygulanmalıdır. Docker image/package indirmeleri yalnız kurulum/build aşamasındadır; çevrimdışı ortama önceden image aktarılabilir. Docker Desktop'ta internal-only ağların host port yayınını engellemesi nedeniyle demo özel bridge tercih eder.

## Fiziksel ve protokol sınırı
GridSentinel hiçbir kesici/koruma cihazına yazmaz. ABB diagnostic tetikleme, reset, konfigürasyon ve MPR setpoint yazımları uygulanmaz. Modbus TCP bridge yazma fonksiyonlarını reddeder. Modbus TCP protokolünde kimlik doğrulama/şifreleme yoktur; demo loopback, saha uygulaması ise izinli SCADA ağı ve firewall allowlist gerektirir. Gerçek OT ağına bağlantı yapılmadı.

## Şirket içi saha uyarlaması
OT ve IT ayrı VLAN/subnet; yalnız gateway dışa telemetri akışı, broker/ingestion hedefleri allowlist. RS485'te ikinci master eklenmez: mevcut RTU'dan veri paylaşımı veya onaylı ayrı port/gateway gerekir. RF sensör kimliği, şifreli bağlantı, commissioning prosedürü ve kabin kapalıyken kapsama doğrulaması gereklidir. TLS/mTLS, kurum PKI, NTP, disk şifreleme, sunucu patch yönetimi, yedek/geri dönüş ve saklama süreleri kurum politikasıyla tamamlanmalıdır.

## Prototip sınırlamaları
Yerel HTTP demo şifrelenmemiştir; uzak erişime açılmadan TLS reverse proxy gerekir. SessionStorage bearer token JavaScript erişimine açıktır; XSS'e karşı daha güçlü üretim oturum tasarımı (HttpOnly/SameSite cookie + CSRF) değerlendirilmelidir. Token/rate limit yapılandırması ve tek süreç kısıtları yatay ölçeğe taşınmadan gözden geçirilmelidir. Mock bildirim gerçek mesaj göndermez. Veritabanı sırlarını çalışan container yönetiminden okuyabilen host yöneticisi güvenilen aktördür.

DB kesintisinde uygulama başarılı ingest cevabı vermez; publisher'ın MQTT PUBACK alması uygulamanın DB transaction commit'i anlamına gelmez. Subscriber kalıcı broker oturumu, bounded8192 frame kuyruğu ve transaction sonrası manual ACK uygular; geçici DB arızası yeniden denenir. Yeniden bağlantı ve DB outage sırasında gönderilen frame'in tek kayıt olarak teslimi test edilir. Fiziksel edge spool yalnız konsepttir. Uzun kesintide tam teslim garantisi için disk kapasitesi, broker retention, dolan kuyrukta reconnect/backpressure ve güç kaybı koşulları ayrıca doğrulanmalıdır.

## Kaynaklar
Mosquitto anonim erişim/parola seçenekleri: [resmî konfigürasyon](https://www.mosquitto.org/man/mosquitto-conf-5.html), [kimlik doğrulama yöntemleri](https://www.mosquitto.org/documentation/authentication-methods/). Container yaklaşımı: [FastAPI Docker belgesi](https://fastapi.tiangolo.com/deployment/docker/). Bunlar yazılım uygulama referanslarıdır; teknik cihaz adreslerinin kaynağı verilen PDF'lerdir.
