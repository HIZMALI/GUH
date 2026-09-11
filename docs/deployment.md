# On-premise dağıtım

Kurulum komutları `install-guide.md` içindedir. `docker-compose.yml` tek host'ta PostgreSQL, Mosquitto, FastAPI ingestion/risk, simulator, read-only Modbus TCP bridge ve Next.js başlatır. Varsayılan100 sentetik pano. `PANEL_COUNT` ile ölçek denemesi yapılabilir; `performance.md` gerçek ölçümleri içerir.

İlk kurulumda internetten image ve paket indirilir. Runtime public cloud bağlantısı gerektirmez; Compose özel bridge ağı ve loopback port yayınları kullanır. İnternet egress kısıtlaması host firewall ile yapılır. Tam air-gap teslim için kontrollü build host'ta image'ları `docker save` ile arşivleyip şirket içi host'a `docker load` ile aktarın; ardından `docker compose up -d --no-build --pull never` kullanın. Gerçek kuruma dağıtım yapılmadı.

Kalıcı veriler `postgres-data` ve `mqtt-data` volume'larında. Zaman serisi ve alarm/audit PostgreSQL'dedir. Düzenli `pg_dump` ve geri yükleme tatbikatı önerilir. Volume yedeği çalışma sırasındaki transaction tutarlılığını tek başına garanti etmez. TimescaleDB bu prototipte kullanılmıyor; time-series indeksleri kullanılıyor, üretim retention/partition policy ayrıca belirlenmeli.

Yerel portlar: web3000, api8000, mqtt1883, scada1502. DB internal5432. TLS demo Compose'da yok; kurum içi uzak istemciler için reverse proxy ve sertifika gereklidir. OT/IT ayrımı, ACL, sır yönetimi ve MQTT teslim sınırları `security.md` içinde.

Single-process risk state ve ingest sıralaması korunur. API worker sayısını ölçüm yapmadan artırmayın. Yatay ölçek için panel-key partitioning, durumu paylaşan risk workers, transaction/order guarantees gerekir. Bridge unit1..247 sınırı kayıt sayısından bağımsız protokol/adresleme tasarımıdır.
