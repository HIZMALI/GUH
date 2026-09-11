# ABB TVOC-2-COM — salt okunur izleme

Kaynak: `1SFC170017M0201_Rev_D_TVOC-2_Modbus_Manual.pdf`, verilen RevD, s.20–33. Sürücü `services/modbus/devices/tvoc2.py`. **TVOC-2-COM gerekir**; çıplak TVOC-2 için koşulsuz Modbus desteği iddia edilmez. Koruma işlevi ABB Arc Guard'da kalır. GridSentinel diagnostic başlatmaz, trip sıfırlamaz, saate veya setpoint'e yazmaz.

S.20–21: **PDU taban0**, register numarası isteyen araçta +1; RTU RS485 2-wire, FC03/04 aynı okuma adresleri. Kaynak varsayılanları19200/even/8bit/1stop; parity none kullanımı2stop gerektirir. ModbusID248 haberleşmeyi devre dışı bırakır; bu sürücü1..247 kabul eder. Kimlik, baud/parity ve COM varlığı sahada yetkili personelce doğrulanır.

Bu tabloda tüm alanlar **1×16-bit unsigned word**, ham/bayt/bit veya tabloda gösterilen tarih kodlaması; ölçek1. Kaynak çok word'lü bir IEEE float kullanmaz. Trip detector low/high ayrı bit alanlarıdır; genel endian çeviricisiyle iki word yer değiştirilmez.

| PDU adresi | Alan / yorum | Kaynak sayfa |
|---|---|---|
| 100–105 | Trip1 detector low/high, relay, date,HHMM,SS | 21 |
| 107–112,114–119,121–126,128–133,135–140,142–147 | Trip2..7, aynı6 alan, **7 adres stride** | 21–22 |
| 149 | Trip sayısı | 22 |
| 200–205 | Diagnostic error date,HHMM,SS,DTC2/1,DTC4/3,DTC6/5 | 22 |
| 206–212 | Diagnostic trip indicator,date,HHMM,SS,detector low/high,relay | 22 |
| 220–221 | Son diagnostic date,HHMM | 22 |
| 222/223 | X2/X3 sensor status, **firmware>=03.00.00** | 22,29 |
| 224/225 | X2/X3 ambient light, **firmware>=03.00.00** | 22,29 |
| 300–305 +7×(n−1), n=1..6 | Error log:date,HHMM,SS,DTC2/1,DTC4/3,DTC6/5 | 22–23,28 |
| 342–347,349–354,356–361 | Error7..9, **yalnız firmware<03.00.00** | 23 |
| 368 | Error sayısı | 23 |
| 370–393 | Altı hata için X2/X3 sensor/ambient snapshot,4-word stride; **firmware>=03.00.00** | 23–24 |
| 500 | Takılı modüller bit alanı | 24,30 |
| 600 | DIP raw word; DIP anlamı cihazdaki ayara bağlı | 24,30 |
| 800/801 | Arc Monitor firmware XXYY / ZZ | 24,30 |
| 1200 | Son Modbus hatasına konu olan PDU adresi | 26,33 |
| 1300 | System state | 26,33 |
| 1301–1306 | DTC n1..n6, her word düşük byte | 26,33 |

800/801 önce okunur: `XX=(word0>>8),YY=word0&255,ZZ=word1&255`. Örnek0x0300,0 →03.00.00. Firmware bilinmiyorsa222–225 **okunmaz**. Standart poll ilk trip, diagnostic, counters, module/DIP, firmware ve state/active DTC okur. Tam hata/trip geçmişi ayrı read ranges ile alınabilir; sürücü meta haritasında yer alır. Gap106,113,.. boşluklarını kapsayan blok okumak yerine her6-word kayıt ayrı okunmalıdır.

S.26–27: unused trip kaydı tüm word'lerde`0xFFFF` →`present:false,quality:missing`; kısmi sentinel veya geçersiz saat →invalid. Gün sayısı1970-01-01'den; HHMM yüksek byte saat, düşük byte dakika, SS0..59. Örnek17078/0x0922/12 →2016-10-04 09:34:12. **Manual saat dilimini belirtmez.** `TVOC2(device_timezone=...)` ile cihazın devreye alınmış saat dilimi verilerek UTC'ye çevrilir. Demo varsayılanıUTC'dir, doğrulanmış cihaz saat dilimi değildir. API alınma saati ile kaynak olay saati ayrı tutulmalıdır.

Detector low bit0..9=X1:1..10; bit10..14=X2:1..5. Detector high bit0..4=X2:6..10; bit5..14=X3:1..10. Her iki word'de bit15 kullanılmaz. Relay bit0=K4,bit1=K5,bit2=K6; bunlar **okunan trip metadata**'sıdır. K4/K5/K6'ya komut gönderilmez.

System state1300 bit0=active trip,bit1=active error,bit2=startup,bit3=diagnostics. Eski trip log'unda kayıt bulunması güncel active trip demek değildir; `event` yalnız state bit0'dan gelir. `latest_trip` tarihsel kaydı açıkça ayrıdır.

Diagnostic DTC203..205 veya303..305: düşük byte n1/n3/n5, yüksek byte n2/n4/n6; HMI yazımı n6-n5-n4-n3-n2-n1. Bunlar altı bağımsız arıza kodu değildir. Kaynak s.28'in son DTC örneğinde adresler tekrarlanmıştır; gerçek adresler s.22–23 tablosundan alınır. Modül500 bit2=X2,bit3=X3; takılı olmayan extension için sahte durum üretilemez.

**Sensor bit polaritesi:** s.29'da1=OK,0=error/warning. Ancak s.27 aktif sensor hatası yokken bu blokların0 olabildiğini söyler. Bu yüzden aktif hata bağlamı yokken bütün sensörler arızalı diye yorumlanmaz; `no_active_error`/null döner. Aktif hata varsa yalnız takılı extension'ların bitleri çözülür. Sensor/ambient alanı firmware bilinmiyorsa`firmware_unknown`, eskiyse`unsupported_firmware` olur.

W213 perform diagnostics, W1000 reset ve RW1100/1101 saat dahil hiçbir yazma çağrısı uygulanmaz. Transport yalnızFC03/04 üretir. TCP→RTU gateway ile saha bağlantısı tasarlanmıştır; TVOC-2'nin native TCP sunucusu olduğu iddia edilmez. Gateway ve RTU kablo terminasyon/bias planı `hardware/schematic/interfaces.md` içinde.

Testler source-date örneğini, UTC dönüşümünü, detector sınır bitlerini, relay/state bitlerini, sentinel'i, DTC sırasını, firmware gating'i, sensor polaritesini ve offline davranışını doğrular. Fiziksel ABB cihazı ile commissioning veya koruma işlevi test edilmedi.
