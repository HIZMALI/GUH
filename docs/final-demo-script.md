# Beş dakikalık final demo — Türkçe

Hazırlık: `python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation`. Yerel [dashboard](http://localhost:3000), `.env` admin bilgileri, PNL001 seçili. Geçmiş silinmez; mevcut çalışma varsayılandır. Sunum sırasında kesinti/load testi çalıştırmayın.

| Süre | İşlem | Söylenecek metin |
|---|---|---|
| 0:00–0:30 | Filo500, risk sıralaması/haberleşme | “GridSentinel AG panoda elektrik, ısınma, nem ve PD belirtilerini birlikte izleyen şirket içi karar destek prototipidir. Bütün gözlemler sentetiktir.” |
| 0:30–1:15 | PNL001 MPR/ABB/sıcaklık/H1/gateway şeması | “Verilen1600kVA çizimini esas aldık. Mevcut MPR/ABB yatırımını yeniden kullanıyoruz. H1 sağ yardımcı devrelerin TH-A hava alanında. Kart, RF ve A/B/C kurulum planımız var.” |
| 1:15–2:30 | Tek tık Termal+PD, yeni run/adım0, risk katkıları | “Temiz NORMAL başlar. Yalnız bu pano1,5s sentetik adımla ilerler; diğer499 pano raporlamayı sürdürür. Sıcaklık/PD birlikte yükselirken ATTENTION, WARNING, CRITICAL oluşur.” |
| 2:30–3:00 | Timeline/aksiyon; gerekirse tüm geçmiş | “Uyarı ve kritik ayrı kalıcı kayıtlardır; fark sentetik adım sayısıdır. Gerçek sahada kaç dakika önce arıza bulduğumuz iddiası değildir. Puanın katkıları ve öneri görünür.” |
| 3:00–3:30 | Tek tık Ark demosu; dedektör/röle/zaman | “Bu ayrı ABB olay simülasyonudur. Sertifikalı koruma bağımsızdır. GridSentinel olayı okur; kesici açtırmaz veya cihaz sıfırlamaz.” |
| 3:30–4:00 | SCADA → PNL500 | “Gerçek yerel TCP okuması: bank3, port1504, unit6. Üç bank500 panoyu kapsar. Kaynak MPR/TVOC adresleriyle bize ait çıkış haritası ayrıdır; ADM/GDZ resmî haritası değildir.” |
| 4:00–4:30 | Aksiyonlar/Alarmlar/Bildirimler | “Yeni/yükselen alarm olay, audit ve mock SMS/WhatsApp kaydı üretir. Durum simulated. Gerçek mesaj gönderilmez; aynı gözlem tekrar bildirim değildir.” |
| 4:30–5:00 | Yaygınlaştırma ölçümü/paket/boş TCO; Kurulum | “100,250,500 cihazın gerçek commit ölçümü burada. CORE, THERMAL, ADVANCED PD ihtiyaca göre yatırım sağlar. Teklif olmadan fiyat/ROI uydurmuyoruz. Retrofit, korelasyon, açıklanabilir risk ve yerel SCADA birlikte çalışır.” |

Nominal combined: step19 ATTENTION,21 WARNING,31 CRITICAL; lead10 sentetik adım. Arc step8. Gerçek süreyi [runtime raporundan](verification/v2-runtime.json) söyleyin; host yükü süreyi etkiler. Hedef combined≤75s/arc≤20s. Timer senaryo seçiminden başlar; hızlandırma fiziksel öngörü süresi değildir.

## Kısa jüri cevapları

| Soru | Cevap |
|---|---|
| Neden AI değil? | Etiketli saha arızası verimiz yok. Açıklanabilir kurallarla neden/kalite sınırını gösterebiliyoruz; AI doğruluk iddiası üretmiyoruz. |
| Neden kablosuz? | Yeni düşük hızlı çevresel sensörlerde kablo müdahalesini azaltır; mevcut Modbus kablolu, geniş bant PD acquisition ayrı. Metal pano RF testi gerekir. |
| 500 pano gerçekten çalışıyor mu? | 500 ayrı sanal kimlik mesaj üretir; gerçek commitler raporda. SCADA üç bankla hepsini adresler. Fiziksel500 pano kurulmadı. |
| Gerçek sahada nasıl kurulur? | Yetkili keşif, gerilim/izolasyon/RF değerlendirmesi, pilot sensör/Modbus doğrulaması, eşik ayarı ve kontrollü kabul gerekir. Kart/firmware referansı bunu somutlaştırır. |
| Planlı kesinti gerekir mi? | Erişim/işleme göre A/B/C matrisi kullanılır. Bara/terminal, besleme ve ilgili montajlar kesinti gerektirebilir; evrensel kesintisiz kurulum sözü yok. |
| SCADA entegrasyonu gerçek mi? | Yerel master ve ayrı bridge arasında gerçek TCP paketleri okundu; gerçek ADM/GDZ merkezine bağlanılmadı. |
| PD ölçümü gerçek mi? | Hayır. HFCT/acquisition yaklaşımı kaynaklı; demodaki özellikler sentetik. Kalibre analog ön uç ve saha testi gerekir. |
| Bu sistem kesiciyi açar mı? | Hayır; izleme/karar desteği. ABB koruması bağımsız; Modbus yazma/trip/reset yok. |
| Maliyeti ne? | Tedarikçi teklifi yok. Kullanıcı girdileriyle pano/filo TCO; fayda ve geri ödeme ancak açık ek varsayımla hesaplanır. |
| Neden yenilikçi? | Mevcut cihazı koruyan retrofit, sinyal korelasyonu, veri kalitesi, açıklanabilir risk, yerel SCADA ve kademeli yatırım birleşir. Patent/üstünlük iddiası değil. |

Bağlantı uyarısı varsa sağlıklıymış gibi geçmeyin. Servis sağlığını kontrol edip yeni normal run ile tekrar deneyin. Tarihli rapor bağımsız test kanıtıdır; o anda canlı ölçülüyormuş gibi sunulmaz.
