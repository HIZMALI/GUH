# GridSentinel demo SCADA register haritası

**Bu yerel harita GridSentinel prototipine aittir; ABB, MPR, ADM veya GDZ haritası değildir.** Tüm gözlemler sentetiktir. TCP bridge gerçek bir yerel socket üzerinde cevap verir; herhangi bir gerçek SCADA veya koruma cihazına bağlanmaz.

`services/scada_bridge/server.py` authenticated`GET /api/fleet` yanıtını varsayılan1s aralıkla okur. Bellekteki tutarlı snapshot'ı ModbusTCP1502 üzerinde FC03/04 ile sunar. HTTP API'deki `/api/scada/registers` bu bridge'e gerçekTCP master isteği yapar; doğrudan DB değerini SCADA okuması diye sunmaz. Standart kütüphane dışında çalışma bağımlılığı yoktur.

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

Panel kimlikleri sayısal son eklerine göre sıralanır: PNL-1,PNL-2,PNL-10. İlk247 kimlik unit1..247.100pano sığar;250 veya500 için bu prototip bridge ilk247'yi sunar ve API daha yüksek paneli422 ile açıkça reddeder. Daha büyük SCADA kapsamı için ayrı endpoint'lerde sabit panel grupları gerekir. **Çoklu bridge gruplama/provisioning bu sürümde uygulanmış değildir.** Demo fleet sabittir; fleet üyeliği değiştirilirse sıra/unit ataması değişebilir. Saha sürümünde kalıcı, gözden geçirilmiş unit mapping gerekir.

FC03/04 normal register okuması desteklenir. Tanımsız unit/range exception02; count0/>125 veya bozuk readPDU exception03; tüm write fonksiyonları (05/06/15/16/22/23 dahil) exception01. MBAP length 2..254 ile gelen ADU en fazla 260 byte olur; bu 12-register haritada başarılı yanıt en fazla 33 byte. Sunucu 64 eşzamanlı bağlantı ve bağlantı başına 120 istek/s sınırı ile 3s idle timeout uygular. Bu sınırlar güvenlik sertifikasyonu veya DDoS dayanım kanıtı değildir.

```powershell
# Repo kökü, yerel kurulumda SERVICE_TOKEN güvenli bootstrap ortamından gelir:
python -m services.scada_bridge.server
# Docker ağı içinde gerçek master doğrulaması (Compose service adı scada):
docker compose exec api python -m services.scada_bridge.master --host scada --port 1502 --unit 1
```

Linux'ta aynı `python -m` ve `docker compose exec` komutları kullanılır. Env:`API_URL=http://api:8000`, `SERVICE_TOKEN` zorunlu, `SCADA_HOST=127.0.0.1` standalone default, `SCADA_PORT=1502`, `SCADA_POLL_INTERVAL=1`, `SCADA_STALE_SECONDS=15`. Compose'da bridge listener0.0.0.0 yalnız container network içindir; host'a/public internete açılmaz. API'nin `SCADA_HOST=scada` değeri master hedefidir.

ModbusTCP uygulama protokolünde kullanıcı kimliği/şifreleme sağlanmaz; allowlist ve ağ segmentasyonu gerekir. UI/API bearer+RBAC ile korunur, bridge API poll restrictedSERVICE_TOKEN kullanır. Yazma yolu ve hardware passthrough yoktur; fiziksel cihaz adapter'ı ayrı bir kod yoludur.

11 Eylül2026: `python -m unittest discover -s tests/modbus -v`24test PASS,0.335s. Bu ölçüm yerel kaynak vektörleri ve localhostTCP/HTTP fixture'ları içindir; Docker veya gerçek OT saha devreye alma sonucu değildir. Runtime kabul ölçümleri root tarafından ayrıca kaydedilir.
