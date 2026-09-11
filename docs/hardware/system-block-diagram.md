# Saha donanım ve veri akışı konsepti

Bu çizimler **hackathon mühendislik konseptidir**. PCB üretimi, EMC/izolasyon/ürün sertifikasyonu veya fiziksel pano kurulumu yapılmadı. Kaynağa dayanan ekipman özellikleri ile yeni öneriler ayrıdır. GridSentinel condition monitoring sağlar; Arc Guard ve diğer koruma cihazları kendi görevlerini sürdürür.

```mermaid
flowchart LR
  subgraph OT[Mevcut pano / OT]
    M[MPR-53CS\nElektriksel ölçümler]
    A[ABB TVOC-2 + COM\nArc event ve diagnostics]
    P[ABB bağımsız koruma yolu]
    A --> P
    T[Yeni kablosuz sıcaklık / nem\nTasarım önerisi]
    H[HFCT30 veya HFCT50\nUygun toprak bağlantısı]
    Q[50Ω koaksiyel + uygun geniş bant AFE\nAcquisition + kalibrasyon + features]
    H --> Q
    M -->|RS485 yalnız FC03/04| E[Edge Gateway\nİzolasyon / kimlik / UTC / kalite]
    A -->|Ayrı RS485 yalnız FC03/04| E
    T -->|Yerel radyo, kabin içinde alıcı| E
    Q -->|Ethernet feature mesajları| E
  end
  subgraph DMZ[OT izleme segmenti / şirket içi sınır]
    F[Firewall allowlist\nSaha gateway outbound bağlantıları]
    E -->|Yerel Ethernet| F
  end
  subgraph LOCAL[On-premise sunucu]
    B[Kimlik doğrulamalı MQTT]
    R[Telemetri / PostgreSQL / Risk]
    U[Dashboard + API RBAC]
    S[Salt okunur Modbus TCP bridge]
    C[SCADA master demosu]
    F --> B --> R --> U
    R -->|Authenticated fleet API| S -->|TCP1502| C
  end
```

Koruma yolu gateway, MQTT, DB veya sunucu kullanılabilirliğine bağlı değildir. Optik detektörler ABB'nin kendi sertifikalı sisteminin parçasıdır; gateway bunları genel amaçlı ADC'ye bağlamaz. Yeni sıcaklık/nem radyo düğümleri yalnız condition-monitoring verisi taşır. Demo sırasında tüm saha bloklarının gözlemleri sentetik generator'dan gelir; yalnız merkez yazılımı ve TCP master gerçek proses/socket olarak çalışır.

Önerilen gateway kategorisi endüstriyel Linux cihazı veya endüstriyel carrier üzerinde MCU+Ethernet sistemidir. Seçim; 2 bağımsız galvanik izole RS485 portu, Ethernet, uygun çalışma sıcaklığı, watchdog, kalıcı kayıt alanı, güvenli anahtar depolama ve yerel radio receiver gereksinimlerine göre yapılır. İki port cihazların baud/parity'lerini ve arıza alanlarını ayırır; var olan RTU bus'a ikinci master doğrudan eklenmez. Uygun arbiter veya onaylı mevcut master üzerinden veri alınır.

Gateway güç/terminal konsepti [arayüz şemasında](../../hardware/schematic/interfaces.md), sensör ve pano yerleşimi [yerleşim belgesinde](panel-placement.md), malzeme listesi [BOM belgesinde](bom.md), kesinti sınıfları [matriste](../installation-matrix.md). Hiçbiri canlı kurulum talimatı veya tamamlanmış üretim tasarımı değildir.
