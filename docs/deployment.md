# On-premise dağıtım

Kurulum komutları `install-guide.md` içindedir. `docker-compose.yml` tek host'ta PostgreSQL, Mosquitto, FastAPI ingestion/risk, simulator, read-only Modbus TCP bridge ve Next.js başlatır. Varsayılan100 sentetik pano. `PANEL_COUNT` ile ölçek denemesi yapılabilir; `performance.md` gerçek ölçümleri içerir.

İlk kurulumda internetten image ve paket indirilir. Runtime public cloud bağlantısı gerektirmez; Compose özel bridge ağı ve loopback port yayınları kullanır. İnternet egress kısıtlaması host firewall ile yapılır. Tam air-gap teslim için kontrollü build host'ta image'ları `docker save` ile arşivleyip şirket içi host'a `docker load` ile aktarın; ardından `docker compose up -d --no-build --pull never` kullanın. Gerçek kuruma dağıtım yapılmadı.

Kalıcı veriler `postgres-data` ve `mqtt-data` volume'larında. Zaman serisi ve alarm/audit PostgreSQL'dedir. Düzenli `pg_dump` ve geri yükleme tatbikatı önerilir. Volume yedeği çalışma sırasındaki transaction tutarlılığını tek başına garanti etmez. TimescaleDB bu prototipte kullanılmıyor; time-series indeksleri kullanılıyor, üretim retention/partition policy ayrıca belirlenmeli.

Yerel loopback portları: web3000, api8000, mqtt1883, SCADA1502–1504. DB internal5432. TLS demo Compose'da yok; kurum içi uzak istemciler için reverse proxy ve sertifika gerekir. OT/IT ayrımı, ACL, sır yönetimi ve MQTT teslim sınırları `security.md` içinde.

Tek API süreci kullanılır. Süreç içi kilit run/revision/focus seçimlerini sıralar; çoklu worker/replica için DB transaction/advisory lock, revision CAS, migration kilidi ve panel-key partitioning gerekir. Worker sayısını bu mekanizmalar ve testler olmadan artırmayın. V2 stable run/step mesaj kimliği ve kalıcı unique indekslerle restart tekrarlarını engeller; nullable migration eski geçmişi tahminî run'a atamaz.

SCADA üç bankla500 panoyu kapsar:247+247+6 unit. `SCADA_PORT_BASE=1502`, `SCADA_BANK_SIZE=247`, `SCADA_BANK_COUNT=3`; Compose yayın aralığı için `SCADA_PORT_END=1504` ve kural END=BASE+COUNT−1. Kapasite COUNT×SIZE; daha büyük filo için bank sayısı/port aralığı birlikte ayarlanır. Her bank aynı salt okunur GridSentinel output map'i kullanır. [Harita](scada/register-map.md).

500 panolu normal demo başlangıcı `python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation`; geçmişi silmeden genişletir. Tek focus1,5s ve toplam50frame/s, kalan499 için yaklaşık10,115s. [Referans firmware](hardware/firmware.md) host üzerinde derlenebilir; fiziksel MCU kurulumu ve laboratuvar doğrulaması ayrı kapsamdır. İlk paket indirmeleri dışında çalışma zamanı haricî servis/font/CDN gerektirmez.

V2 kesinti testi sırasında DB geri geldikten sonra pano okumasında20s istemci timeout'u görüldü; önceki denemeler kabul kaydında saklandı. Artık bağlantı/havuz3s, SQL statement/socket5s, SQL lock2s ve uygulama write-lock3s varsayılan sınırları var. `.env.example` anahtarlarıyla yapılandırılır. API salt-okuma yolları maintenance yazma kilidini beklemez; aynı risk/policy fonksiyonu eski gözlemi unavailable yansıtır, arka plan tick'i kalıcı alarmı işler. API container DNS `timeout:1, attempts:1` kullanır; yalnız connect timeout tüm DNS beklemesini sınırlamaz. [Docker dns_opt](https://docs.docker.com/reference/compose-file/services/#dns_opt), [PostgreSQL libpq bağlantı seçenekleri](https://www.postgresql.org/docs/16/libpq-connect.html). Bunlar her ağda matematiksel uçtan uca gecikme garantisi değildir; final gerçek restart testiyle doğrulanır.


## Windows host port eşlemesi

Windows/Hyper-V yeniden başlatma sonrası bazı TCP aralıklarını ayırabilir. `netsh interface ipv4 show excludedportrange protocol=tcp` ile kontrol edilir. 11 Eylül 2026 son yerel çalışmada 1502–1504 ve 1883 bu aralıklardaydı. İşletim sistemi rezervasyonları değiştirilmeden `.env` içine şu yalnız-host ayarları kondu:

```dotenv
SCADA_HOST_PORT_BASE=11502
SCADA_HOST_PORT_END=11504
MQTT_HOST_PORT=11883
```

`docker compose up -d` ile uygulanır. Host aralığı `SCADA_BANK_COUNT` kadar port içermelidir. İç banklar 1502/1503/1504, iç MQTT 1883 kalır; API gerçek TCP master `scada:1504`, unit6 üzerinden PNL-500'ü okur. Host'tan aynı bank `127.0.0.1:11504` ile okunur. Host doğrulama scriptleri bu eşlemeyi `.env` içinden kullanır. Opsiyonel host değişkenleri yoksa eski 1502–1504/1883 davranışı korunur; `.env` pakete girmez.
