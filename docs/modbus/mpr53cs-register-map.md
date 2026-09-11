# MPR-53CS — kaynak temelli salt okunur harita

Kaynak: `MPR-53CS_Modbus_Register_Map_EN.pdf`, 01.12.2019, **s.1**, doğrudan tarama incelemesi. Okunur döndürülmüş inceleme kopyası `tmp/pdfs/mpr-readable.png`; asıl PDF değişmedi. Sürücü: `services/modbus/devices/mpr53cs.py`. Yapılandırma/setpoint s.2 kullanılmaz. GridSentinel koruma rölesi değildir.

**Adres düzeltmesi:** Sütundaki toplam güçler 44/46/48/50/52; frekans **58**; THD **72–82**; dijital çıkış **84**, giriş **85**; ilk enerji **86**. Bunlar taramadaki gerçek adreslerdir. Frekans54 / dijital giriş80 / enerji88 gibi önceki çalışma özetleri kaynak taramasına uymamaktadır.

Kaynağın `ADDRESS`/hex adresi doğrudan **PDU taban0** kabul edilir. İlk adres0'dır; 40001 biçimindeki arayüzlerde gösterim ofseti ayrıca ayarlanmalıdır. Adrese sürücü içinde +1 eklenmez. `int`/`unsigned int` ve 2-adres adımı 32-bit tamsayı, birleşik enerji satırı ve 4-adres adımı 64-bit olarak uygulanır. Modbus her word içinde big-endian; **word sırası belgede belirtilmemiştir**. `MPR53CS(word_order="big"|"little")` değiştirilebilir; varsayılan `big` sahada doğrulanmamıştır. Fiziksel cihazla ekran karşılaştırması yapılmadan doğru word order iddiası yoktur.

| PDU adresi | Veri | Word / signedness | Çarpan | Birim |
|---|---|---|---|---|
| 0,2,4 | L1/L2/L3 faz gerilimi | 2 / uint32 | 0.1 | V |
| 6,8,10;12 | L1/L2/L3; nötr akımı | 2 / uint32 | 0.001 | A |
| 14,16,18 | L1-L2/L2-L3/L3-L1 gerilimi | 2 / uint32 | 0.1 | V |
| 20,22,24 | Faz aktif güç | 2 / int32 | 0.1 | W |
| 26,28,30 | Faz reaktif güç | 2 / int32 | 0.1 | var |
| 32,34,36 | Faz görünür güç | 2 / uint32 | 0.1 | VA |
| 38,40,42 | Faz cosφ | 2 / int32 | 0.001 | oran |
| 44,46 | Toplam import / export aktif güç | 2 / int32 | 0.1 | W |
| 48,50 | Toplam endüktif / kapasitif reaktif güç | 2 / int32 | 0.1 | var |
| 52 | Toplam görünür güç | 2 / uint32 | 0.1 | VA |
| 54,56 | Ortalama endüktif / kapasitif cosφ | 2 / int32 | 0.001 | oran |
| 58 | Frekans | 2 / uint32 | 0.01 | Hz |
| 60,62,64;66,68,70 | Gerilim; akım faz açıları | 2 / uint32 | **1** | derece |
| 72,74,76 | Faz gerilim THD | 2 / uint32 | 0.1 | % |
| 78,80,82 | Faz akım THD | 2 / uint32 | 0.1 | % |
| 84;85 | Dijital çıkış; dijital giriş durumu | 1 / **ham uint16 yorumu** | 1 | ham |
| 86,90,94,98 | Import aktif / export aktif / endüktif reaktif / kapasitif reaktif enerji1 | 4 / uint64 yorumu | 1 | Wh / Wh / varh / varh |
| 102,106,110,114 | Aynı enerji türleri, sayaç2 | 4 / uint64 yorumu | 1 | Wh / Wh / varh / varh |

Dijital durum84/85 kaynakta **R** işaretli; ancak format, ölçek ve bit tanımları boş. Komşu adreslere göre tek ham word okunur. Belirli rölenin açık/kapalı olması uydurulmaz. Enerji formatı `long int` yazsa da kaynak aralığı `0..FFFFFFFFFFFFFFFF`; uygulama işaretsiz64 yorumunu ve bu yorumu metadata notunda korur. Enerjide `0xFFFFFFFFFFFFFFFF` bir ABB trip sentinel'i gibi yorumlanmaz.

| PDU blokları | Kaynak s.1 anlamı | Word / signedness / çarpan |
|---|---|---|
| 118,120,122 / 124,126,128 | Min faz / fazlar arası gerilim | 2 / uint32 /0.1V |
| 130,132,134 | Min faz akımı | 2 / uint32 /0.001A |
| 136,138,140 / 142,144,146 | Min faz aktif / reaktif güç | 2 / int32 /0.1W veya var |
| 148,150,152 | Min faz görünür güç | 2 / uint32 /0.1VA |
| 154,156,158,160;162 | Min toplam import/export aktif, import/export reaktif; görünür | 2 / int32 ilk4, uint32 son /0.1 |
| 164–208, aynı sıra ve 2 adım | Yukarıdaki min alanlarının max karşılıkları | Aynı tip/ölçek |
| 210,212,214 | Max faz akım demand | 2 / uint32 /0.001A |
| 216,218,220;222,224,226 | Faz import; export aktif güç demand | 2 / int32 /0.1W |
| 228,230,232;234,236,238 | Faz import; export reaktif güç demand | 2 / int32 /0.1var |
| 240,242,244 | Faz görünür güç demand | 2 / uint32 /0.1VA |
| 246,248,250,252;254 | Toplam import/export aktif, import/export reaktif; görünür demand | 2 / int32 ilk4, uint32 son /0.1 |

Min/max/demand satırları kaynakta R/W olabilir; sürücü yalnızca okur. Pulse/hour counter256–264 kaynakta HEX ve ayrı alanlar; ilk sürümde anlamlandırılmaz. 32768+ ayarlar veya 33280+ setpoint'ler okunabilir bir anlık durum alanı yerine kullanılmaz.

Hızlı poll0..85 toplam86 word, FC03. Standart read-only TCP→RTU gateway üzerinden `ReadOnlyTCPGateway` kullanılır; bu MPR'nin native TCP desteklediği anlamına gelmez. Enerji veya min/max istenirse ayrı FC03 bloklarıyla okunur, `decode(address_word_dict,names)` çağrısına geçirilir. Timeout/invalid/missing ayrıdır; kayıp veri0 yapılmaz. Cihaz CT/VT ayarını uygulamış primer ölçümü tekrar CT ile çarpılmaz. W→kW gibi API birim dönüşümleri ayrıca `/1000` olur; import/export/indüktif/kapasitif alanlar sahadaki hesaplama modu bilinmeden tek net güç sayısına birleştirilmez.

Doğrulama: 11 Eylül2026, kaynak literal adres vektörleriyle 231V,318A, -100W,-0.9cosφ,50Hz,7.3% THD,64-bit enerji, iki word sırası ve timeout test edildi. Fiziksel MPR, CT ayarı veya bus devreye alma yapılmadı.
