# Konsept BOM ve satın alma sınırı

Donanım satın alınmadı. Aşağıdaki liste tek pano için **örnek kapsam/teklif toplama listesidir**; gerçek fiyat teklifi, üretim onayı veya tam kablolama listesi değildir. Verilen kaynaklar fiyat içermez. Bu nedenle maliyet sütunları `teklif_gerekli`; uydurulmuş piyasa fiyatı veya sahada doğrulanmış tasarruf iddiası yoktur. Makine okunur liste `hardware/bom/indicative-bom.csv`.

| Kategori | Adet / ilk pano | Asgari konsept gereksinimi | Maliyet durumu |
|---|---:|---|---|
| Edge gateway | 1 | Yerel işlem, kalıcı kuyruk, Ethernet, watchdog, kimlik yönetimi | teklif gerekli |
| İzole RS485 arayüz | 2 port | Ayrı device bus, surge/ESD/izolasyon tasarım doğrulaması | gateway içinde veya ayrıca teklif |
| 24VDC yardımcı besleme | 1 | Onaylı SELV/PELV kaynak, güç bütçesi ve saha koordinasyonu | teklif gerekli |
| Kablosuz yüzey sıcaklık sensörü | 6 | Örnek üç üst/üç seçilmiş çıkış noktası, uygun izolasyon/montaj/çalışma sıcaklığı | teklif gerekli; adet site riskine göre |
| Kablosuz sıcaklık+nem sensörü | 1 | Ortam ölçümü, kimlik, pil/kalite durumu | teklif gerekli |
| Radyo alıcı | 1 | Kabin içi veya uygun anten düzeni, yerel veri teslimi | gateway içinde veya ayrıca teklif |
| HFCT30 **veya** HFCT50 | 1 opsiyon | 30/50mm uygun toprak bağlantısı,50Ω BNC; verilen datasheet koşulları | teklif ve uygunluk gerekli |
| PD acquisition/AFE | 1 opsiyon | Geniş bant, kalibrasyon, gürültü ayrımı, feature işleme | uzman teklif gerekli; HFCT'den ayrı maliyet |
| Endüstriyel enclosure / DIN / terminaller | 1 set | Yerel montaj şartlarına uygun kutu, klemens, kablo rakoru, etiket | teklif gerekli |
| Data kablosu ve koruma aksesuarı | 1 set | İzole RS485,2 uç terminasyon, kontrollü bias,Ethernet; saha uzunluğu bilinmiyor | metre/terminal keşfi sonrası |
| MPR-53CS ve TVOC-2-COM | Mevcut varsayımı | Sahada mevcutluk/firmware/COM doğrulaması gerekir | yeni alım gerekiyorsa ayrıca teklif |

HFCT30 kaynağı s.1:1–60MHz,42MHz/50Ω'da maksimum17mV/mA,30mm delik,−20…+70°C,25kVpeak/1saat sensör izolasyon verisi. HFCT50 kaynağı s.2:−6dB band1–80MHz,aynı hassasiyet/50Ω,50mm delik,111×123×38mm,−20…+70°C. Bu değerler gateway veya pano bütününün izolasyon/sertifikasyonunu göstermez. Daha büyük çap üreticiye özel doğrulatılır.

Maliyet modeli: `gateway + güç/RS485 + N_sıcaklık×sensör + N_nem×sensör + montaj + keşif/devreyealma + bakım/pil + opsiyonel PD`. Sunucu maliyeti pano başına bölünebilir; izolasyon/OT izin çalışması, planned outage ve acquisition kalibrasyonu dışarıda bırakılmamalıdır. Fayda değerlendirmesi için saha false alarm oranı, bulunabilir arıza modları, operatör zamanı ve gerçek bakım sonuçları gerekir; sentetik test bunları ölçmez.
