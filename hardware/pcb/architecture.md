# Carrier mimarisi ve arayüz kararları

ESP32-S3-WROOM-1U, 3.3 V MCU/radyo modülü referans adayıdır. ESP32-S3 üzerinde bu tasarıma yeterli yerleşik Ethernet MAC/PHY varsayılmaz; SPI üzerinden WIZ850io kullanılır. WIZ850io W5500, PHY, transformer ve RJ45'i tek modülde birleştirir. Böylece referans carrier üzerinde yüksek hızlı Ethernet çiftlerinin ve magnetics'in yeni bir tasarım olduğu izlenimi verilmez. Yerel işletme verisi Ethernet üzerinden on-premise broker'a yönelir; Wi-Fi zorunlu bağlantı değildir. Kablosuz sensör alımı, teknik olarak uygunsa BLE sınıfı receiver portuyla temsil edilir. Metal kapak altında RF test edilmedi.

Güç ağacı: **J1 +24 VDC auxiliary → F1 → ters kutup D1 → TVS1 / L1 / C1 → DC1 5 V → DC2 3.3 V**. Ayrıca 5 V ana hattan **iki ayrı** izole DC/DC, V5_MPR/GND_MPR ve V5_TVOC/GND_TVOC üretir. U3/U4 ISO1410 logic tarafları V3V3/GND_LOGIC; field tarafları kendi izole 5 V/common'larıdır. İzole güç ile sinyal izolasyonu beraber gerekir. ISO1410 tek başına izole besleme üretmez.

J1 üçüncü ucu ve J2/J3 ekran uçları CHASSIS adını taşır. CHASSIS, GND_LOGIC, GND_MPR ve GND_TVOC ayrı netlerdir. Son tesis ekran/PE bağlantısı saha EMC ve topraklama incelemesine bağlıdır; ekranı rastgele COM'a birleştiren jumper yoktur. Ethernet kablo çiftleri module magnetics arkasındadır; CSV'de ETH_CABLE domain olarak ayrılır. J4 entegre RJ45'i gösterir, ikinci bir carrier RJ45 footprint'i değildir. J5 U1 üzerindeki gerçek harici anten connector'ıdır; carrier'da uydurma RF pad tanımlanmaz.

| İşlev | U1 pad / GPIO | Karar |
|---|---|---|
| MPR UART TX / RX / DE+RE | 10/G17, 11/G18, 8/G15 | Ayrı RTU portu, DE+RE 10 kΩ pull-down ile başlangıç receive |
| TVOC UART TX / RX / DE+RE | 4/G4, 5/G5, 6/G6 | Ayrı RTU portu; ABB varsayılan 19200 8E1 commissioning'de doğrulanır |
| Ethernet CS / MOSI / SCK / MISO | 18/G10, 19/G11, 20/G12, 21/G13 | WIZ850io H_ETH1/H_ETH2 doğrulanmış pinleri |
| Ethernet INTn / RSTn | 17/G9, 22/G14 | RST yalnız Ethernet module'ünü etkiler |
| SPI NVM CS | 23/G21 | Ethernet ile SPI paylaşımı; ayrı CS; eşzamanlı erişim HAL tarafından seri hale getirilir |
| Watchdog WDI | 7/G7 | Yalnız MCU EN reset; hiçbir field çıkışı yok |
| J6 USB D+ / D− / BOOT | 14/G20, 13/G19, 27/G0 | Yerel servis; 3.3 V sense giriş beslemesi değildir |
| J7 PD feature RX | 38/G2 | Opsiyonel UART0 RX routing; TX dışarı çıkarılmaz |

GPIO0/3/45/46 strap işlevleri ve varyanta göre GPIO35–37 hafıza kullanımı gözetilir; BOOT dışındaki strap pinleri normal saha I/O'su yapılmaz. Kullanılmayan module padleri NC olarak açık bırakılmıştır. J7 yalnız aynı güvenli düşük gerilim domain'indeki harici acquisition'dan **türetilmiş sayısal feature** alabilir. HFCT30/50 analog MHz sinyali MCU ADC'ye bağlanmaz; PD'nin pC kalibrasyonu yoktur. Harici acquisition'ın Ethernet'i mevcut LAN/J4 üzerinden de kullanılabilir; carrier'da ikinci Ethernet PHY/port iddiası yoktur.

Güç CSV'si 5 V ana hatta yaklaşık **5.131 W**, DC1 için varsayılan %85 verimle 24 V girişte **6.036 W / 0.2515 A** verir. %25 mühendislik rezerviyle **7.545 W / 0.3144 A** bütçe edilir. Bunlar ölçüm veya minimum üretim garantisi değildir; startup/inrush, transient, kabin içi sıcaklık, seçilmeyen NVM/supervisor ve verim eğrileri test edilmelidir. F1 akımı ve TVS clamp seviyesi bu nominal hesaptan otomatik seçilmez. 3.3 V ≥1 A sınıfı ve 5 V ≥1.5 A sınıfı besleme tasarım hedefleri yalnız ön tahsistir; seçili ürün garantisi değildir.

Kalıcı kuyruk referansı 8 frame × 3072 byte payload tutar; iki snapshot ve metadata için NVM'de en az64 KiB tahsis planlanır. Saniyeler ölçeğinde snapshot yazma flash aşınmasını ciddi etkiler; seçili endurance doğrulanmadan dahili flash'a sürekli tam snapshot yazılmaz. FRAM veya aşınma dengeleme, atomik commit ve güç kaybı stratejisi son portta tasarlanmalıdır. NVM modülü seçilmedi; host testte POSIX fsync/rename journal kullanılır.
