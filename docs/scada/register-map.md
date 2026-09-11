# GridSentinel demo SCADA register haritası

**Bu yerel harita GridSentinel prototipine aittir; ABB, MPR, ADM veya GDZ haritası değildir.** Tüm gözlemler sentetiktir. TCP bridge gerçek bir yerel socket üzerinde cevap verir; herhangi bir gerçek SCADA veya koruma cihazına bağlanmaz.

`services/scada_bridge/server.py` authenticated`GET /api/fleet` yanıtını varsayılan1s aralıkla okur. Tutarlı snapshot'ı ModbusTCP1502–1504 banklarında FC03/04 ile sunar. `/api/scada/registers` bu bridge'e gerçek TCP master isteği yapar; DB değerini TCP okuması diye sunmaz. Standart kütüphane dışında çalışma bağımlılığı yoktur.

Tüm adresler **PDU taban0**, her satır bir **uint16**, word içi byte sırası big-endian, ölçek1. Address10/11 birlikte unsigned32 UNIX saniye, high-word first. Kullanıcı aracı40001 biçimi kullanıyorsa PDU0→40001/FC03 veya30001/FC04 gösterimi ayrıca ayarlanır.

| PDU | Alan | Değer / birim |
|---|---|---|
| 0 | health_score | 0..100 son condition-health skoru |
| 1 | risk_score | 0..100 son risk skoru |
| 2 | state | 0NORMAL,1ATTENTION,2WARNING,3CRITICAL |
| 3 | alarm_active | 0/1, backend active-alarm indicator |
| 4 | thermal_alarm | 0/1, pozitif thermal/temperature/hotspot contribution |
| 5 | pd_alarm | 0/1, pozitif PD contribution |
| 6 | arc_event | 0/1, sentetik Arc Guard event metadata |
| 7 | communication_ok | **0/1 geçerlilik kapısı**, aşağıyı okuyun |
| 8 | sensor_health | 0..100 backend sensor quality score; overallhealth ile aynı şey değildir |
| 9 | schema_version | 1 |
| 10 | timestamp_high | Last observed UNIX seconds bits31..16 |
| 11 | timestamp_low | Last observed UNIX seconds bits15..0 |

`0xFFFF` eksik/geçersiz/uygulanamayan alanın açık sentinel'idir; state65535 NORMAL değildir. Kaynakta timezone olmayan/geçersiz saat iki timestampword'ünü65535 yapar. UTC uint32 alan2106 sınırı taşarsa veri uydurulmaz. Önceki skor tutulabilir; timestamp son gözlemin zamanıdır.

Bridge API'ye erişemediğinde **hemen** register7/8=0; son başarılı poll'dan15s geçtiğinde de7/8=0. Stale snapshot'ın önceki state'i NORMAL olsa bile sağlıklı/online gösterilmez. Tüketici **register7=1 ve kabul ettiği timestamp freshness** koşulunu kontrol ederek skorları kullanmalıdır. `connected:true` yalnız master'ın TCP cevap aldığını ifade eder; kaynak gözlemlerin taze olduğu anlamına gelmez. Başlangıçta snapshot yoksa unsupported unit exception02. Bridge yeniden başlayınca yeni API snapshot gelene kadar veri üretmez.

## V2: 500 pano için banka adreslemesi

Panel kimlikleri sayısal son eklerine göre sıralanır. Sıfır tabanlı sıra `i` için banka `floor(i / bank_size) + 1`, unit `i % bank_size + 1`, port `port_base + bank - 1`. API ve bridge aynı `services/scada_bridge/banks.py` eşlemesini kullanır. Unit hiçbir zaman 247'yi aşmaz. Farklı kimliklerin araya eklenmesi sıra atamasını değiştirebilir; saha uygulaması kalıcı ve gözden geçirilmiş adresleme gerektirir.

| Banka | Yerel port | Panolar | Unit |
|---:|---:|---|---|
| 1 | 1502 | PNL-001 … PNL-247 | 1 … 247 |
| 2 | 1503 | PNL-248 … PNL-494 | 1 … 247 |
| 3 | 1504 | PNL-495 … PNL-500 | 1 … 6 |

`GET /api/scada/registers?panel_id=PNL-500` varsayılan yapılandırmada `bank:3`, `port:1504`, `unit_id:6` döndürür ve gerçekten o porttan okur. Son bankada kullanılmayan unit 7 exception02 üretir. Kapasite aşıldığında API422 verir; bridge eksik filoyu sessizce sunmak yerine tüm bankaları unavailable işaretler. Üç listener bağlanmadan servis başlamaz; herhangi bir port çakışması başlangıcı başarısız yapar.

`SCADA_BANK_SIZE=247`, `SCADA_BANK_COUNT=3`, `SCADA_PORT_BASE=1502` değiştirilebilir. `SCADA_PORT` eski standalone kurulumlar için port-base fallback'idir. Docker Compose host yayın aralığı için ayrıca `SCADA_PORT_END = SCADA_PORT_BASE + SCADA_BANK_COUNT - 1` girilmelidir; varsayılan 1504. Örneğin taban1600 ve üç banka için END1602 gerekir. Boyut1..247, banka sayısı1..128, son TCP portu en çok65535 olarak doğrulanır. Host portları yalnız127.0.0.1 üzerinde yayınlanır; API hedefi container içindeki `scada` host'udur. Tek authenticated fleet poll üç bankaya dağıtılır.

FC03/04 normal register okuması desteklenir. Tanımsız unit/range exception02; count0/>125 veya bozuk readPDU exception03; tüm write fonksiyonları (05/06/15/16/22/23 dahil) exception01. MBAP length 2..254 ile gelen ADU en fazla 260 byte olur; bu 12-register haritada başarılı yanıt en fazla 33 byte. Sunucu 64 eşzamanlı bağlantı ve bağlantı başına 120 istek/s sınırı ile 3s idle timeout uygular. Bu sınırlar güvenlik sertifikasyonu veya DDoS dayanım kanıtı değildir.

```powershell
# Repo kökü, yerel kurulumda SERVICE_TOKEN güvenli bootstrap ortamından gelir:
python -m services.scada_bridge.server
# Docker ağı içinde gerçek master doğrulaması (Compose service adı scada):
docker compose exec api python -m services.scada_bridge.master --host scada --port 1502 --unit 1
# PNL-500:
docker compose exec api python -m services.scada_bridge.master --host scada --port 1504 --unit 6
```

Linux'ta aynı `python -m` ve `docker compose exec` komutları kullanılır. Env:`API_URL=http://api:8000`, `SERVICE_TOKEN` zorunlu, `SCADA_HOST=127.0.0.1` standalone default, `SCADA_PORT=1502`, `SCADA_POLL_INTERVAL=1`, `SCADA_STALE_SECONDS=15`. Compose'da listener0.0.0.0 container içindedir; host yayınları yalnız127.0.0.1 üzerindedir. Public internete açılmaz. API'nin `SCADA_HOST=scada` değeri master hedefidir.

V2 yeni koşunun ilk ölçümünü beklerken `pending_current_run=true`, register7/8=0 olur. Önceki skor/timestamp korunabilir fakat geçerlilik kapısı kapanır; eski kritik değer yeni koşuya aitmiş gibi tüketilmemelidir.

ModbusTCP uygulama protokolünde kullanıcı kimliği/şifreleme sağlanmaz; allowlist ve ağ segmentasyonu gerekir. UI/API bearer+RBAC ile korunur, bridge API poll restrictedSERVICE_TOKEN kullanır. Yazma yolu ve hardware passthrough yoktur; fiziksel cihaz adapter'ı ayrı bir kod yoludur.

V1 kanıtı:24 kaynak/transport testi PASS. V2 ilavesiyle `python -m pytest tests/modbus -q` **38 test PASS**:500 panelin her biri ayrı gerçek localhost TCP yanıtındaki timestamp ile doğrulandı; sınırlar, her bankada tüm write fonksiyonları, geçersiz register, unavailable/recovery ve pending-run geçerlilik kapısı denetlendi. Kanıt `docs/verification/v2-modbus-tests.xml`. Bu localhost fixture testi fiziksel OT testi değildir; canlı Docker roundtrip ayrıca V2 runtime kaydındadır.
