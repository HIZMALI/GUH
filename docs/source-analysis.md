# Kaynak analizi

İnceleme: 11 Eylül 2026. Kaynakların SHA-256 özeti ve sayfa/sayfa metin kapsamı `data/source/manifest.json`; ham çıkarımlar aynı dizindedir. Verilen dokuz PDF ve bir Excel incelendi. MPR haritası taranmış olduğundan sayfa görüntülerinden okunmuştur. Teknik çizim de görsel olarak incelendi. Bunlar verilen baskılardır; güncel saha uygunluk onayı değildir.

## Problem, çıktı ve değerlendirme
`Grid Up Hackathon Proje Konusu.pdf`, s.1–5: AG pano/OG hücre arızası öncesinde termal, akım, nem, izolasyon ve PD belirtilerini birleştirip erken uyarı. Saha modül konsepti, elektronik I/O/şema, yazılım, monitoring, Modbus entegrasyon yaklaşımı, bildirim demosu, en az 100 modül ve kaynak değerlendirmesi bekleniyor. On-premise zorunlu; public cloud yok. Fiziksel sensör satın alma/kurulum veya gerçek SCADA bağlantısı gerekmiyor. Değerlendirme: problemi anlama, anomali/risk yaklaşımı, saha uygulanabilirliği, uçtan uca yaklaşım, entegrasyon, ölçeklenebilirlik, operatör deneyimi, maliyet/fayda ve yenilikçilik. Belgede sayısal ağırlık yok.

## 1600 kVA pano
`AG Pano Teknik Çizim-1600kVA.pdf`, tek sayfa, basılı s.51 EK-II/14: MLZ.DSYA 1250–1600 kVA dahili tip. A genişlik 1600 mm, B yükseklik 1500 mm; tolerans +100/-0. C derinlik 450 mm; +50/-0. Alt kablo bağlantı bölgesi en az 400 mm. Üstte düşey giriş baraları ve CT bölgesi, solda sabit kompanzasyon, üst sağda modem/yardımcı alan; ortada DSYA çıkış sırası, sağda ölçü/yardımcı devreler. Şemadaki ek sensör noktaları GridSentinel önerisidir.

`1600kVA AG Pano Teknik Özellikleri.pdf`, Tablo 8, basılı s.34: 1600 kVA ana bara 2×(100×10 mm²) kalay kaplı elektrolitik bakır; CT 2500/5; beş 250 A ve beş 400 A besleme çıkışı + iki yedek. DSYA terminaller arası 185 mm. Sokak aydınlatma girişi 160 A, çıkış sayısı <=4. Bu bilgiler sensör satın alımı veya canlı montaj talimatı değildir.

## TEDAŞ saha koşulları
`AG PANO MALZEME ŞARTNAMESİ.pdf`, TEDAŞ-MLZ/2003-06.B, Haziran 2015 revizyonu: PDF s.5/basılı4 Tablo1: aksi belirtilmezse 2000 m; en çok 40°C, 24 saat ortalama35°C; dahili en az -5°C, harici -25°C. Dahili kirlilik II, harici III; dahili bağıl nem +40°C'de %50, +20°C'de %90; harici +25°C'de %100. PDF s.6/basılı5: 231/400 V, 50 Hz, 1600 kVA ana bara/giriş anma2312 A; kısa devre etken38 kA/tepe80 kA. PDF s.8/basılı7: dahili IP2X, harici IP54. PDF s.9/basılı8: ısınma sınırları TS EN61439-1 Çizelge8'e atıf; bu çizelgenin sayısal limitleri sunulmamış, demo alarm eşikleri oradan türetilmiş gibi gösterilmez. Form2B ve canlı kısımlara erişim önlemleri korunmalıdır. Donanım/yerleşim ekleri kaynak çizimle birlikte değerlendirilmiştir.

## MPR-53CS
`MPR-53CS_Modbus_Register_Map_EN.pdf`, s.1–2, 01.12.2019: s.1 ölçümler ve konfigürasyon; s.2 programlanabilir setpoint'ler. İzleme sürücüsü yazma yapmaz. Döndürülmüş s.1 görüntüsünden doğrulanan adresler: faz gerilim0/2/4; faz akım6/8/10; nötr12; faz-faz gerilim14/16/18; aktif güç20/22/24; reaktif26/28/30; görünür32/34/36; cosφ38/40/42; toplam import aktif44, export aktif46, indüktif reaktif48, kapasitif reaktif50, görünür52; ortalama indüktif/kapasitif cosφ54/56; frekans58; gerilim açı60/62/64; akım açı66/68/70; THD gerilim72/74/76 ve akım78/80/82; dijital çıkış84, giriş85; enerji86/90/94/98/102/106/110/114 (her biri4word). Gerilim ölçeği0.1, akım0.001, güç0.1, cosφ0.001, frekans0.01, THD0.1; açılar1. PDF'deki format/word-order belirsizlikleri sürücü belgesinde açıkça tutulacak. Dijital durumların bit yerleşimi açıklanmıyor; ham word olarak korunur. CT oranı ayrıca uygulanarak ikinci kez ölçeklenmez. Min/max ve demand alanları da haritada bulunur.

## TVOC-2 ve COM
`tvoc.pdf`, özellikle s.5–8: koruma görevi ABB Arc Guard'a aittir; GridSentinel değiştirmez. Modbus RTU için COM modül gerekir; çıplak TVOC-2'de koşulsuz Modbus var denmez. X1/X2/X3 ile en çok30 optik dedektör. Donanım koruması ile monitoring yazılımı ayrı.

`1SFC170017M0201_Rev_D_TVOC-2_Modbus_Manual.pdf`, s.20: RS485 2-wire; FC03/04 aynı adreslerle okuma; default19200/even, adres248 iletişimi devre dışı bırakır. s.21–26 **PDU sıfır tabanlı** adresler: trip1 100–105, sonraki tripler7 offset, toplam149; diagnostic200–212; son diagnostic220–221; X2/X3 sensör222/223, ambient224/225 (firmware>=03.00.00); hata log300+, hata sayısı368; modüller500, DIP600, sürümler800+; Modbus hata1200; state1300 ve aktif DTC1301–1306. S.26–27: kullanılmayan trip0xFFFF; tarih1970-01-01'den gün, HHMM yüksek byte saat/düşük byte dakika. Detector düşük word'de bit0–9 X1:1–10, bit10–14 X2:1–5; yüksek word bit0–4 X2:6–10, bit5–14 X3:1–10. Bit15 kullanılmaz. Relay bit0/1/2 K4/K5/K6. s.33 state bit0 active trip, bit1 active error, bit2 startup, bit3 diagnostic. Diagnostics çalıştırma213 ve reset1000 dahil hiçbir yazma çağrısı uygulanmayacak.

## HFCT ve gerçek acquisition sınırı
`DS_HFCT30_eng.pdf` s.1: 1–60 MHz, 42 MHz/50Ω yükte maksimum17 mV/mA; 50Ω, 30 mm delik, -20…+70°C, 25 kVpeak/1 saat izolasyon; BNC koaksiyel çıkış, sistem toprak bağlantısında uygulama. `DS_HFCT50_eng.pdf` s.2: -6dB bant1–80 MHz, aynı hassasiyet/yük, delik50 mm, dış111×123×38 mm, -20…+70°C. Büyük delik özel üretim ve üretici doğrulaması gerektirir. PD için uygun geniş bant analog ön uç, kalibrasyon, acquisition/sinyal işleme gerekir. Basit MCU ADC veya sentetik feature gerçek PD ölçümü değildir; demo PD genlikleri arbitrary unit, pC kalibrasyonu iddiası yok.

## Excel ve veri kökeni
`İstenen Veriler.xlsx`: `Akım Sensörü` A7:F158 arasında152 satır, 15 dakika aralıklı L1 örnekleri. B sekonder mA, D çarpan6000, E hesaplanan primer A; örnek53mA /1000×6000=318A. E90–540A, medyan297A. A sütunu time/datetime karışık; 1900 tarihleri gerçek saha tarihleri değil Excel süre gösterimidir. B2'de125mA/5A başka CT notu ile B4'te100mA/600A ifadesi birlikte bulunur; sayısal satırlardaki6000 çarpanı kullanılır, 1600kVA ana giriş CT'siyle karıştırılmaz. Kaynak E değerleri ve formülleri importer ile karşılaştırılmalıdır.

`ARC` A1:A2 yalnızca ABB TVOC-2 Modbus okunacağı açıklaması. `PD` A1:A4 HFCT30 ve çalışma mantığı referansı; pulse/time series yok. `Sıcaklık_Nem` tamamen boş. Bu nedenle yalnız L1 organizer_synthetic_replay; diğer bütün sensörler generated_synthetic. Zaman damgası ve faz üretimi açık varsayım. Hiçbir veri gerçek sahadan alınmış değildir.

## Açık doğrulama sınırları
Gerçek cihaz/firmware/CT ayarı, Modbus word order, RF kapsama, pil ömrü, alarm eşikleri, kabin içi montaj uygunluğu ve acquisition kalibrasyonu sahada doğrulanmamıştır. Fiziksel kurulum sınıfları ve kablosuz seçimler tasarım önerisidir. Prototip SCADA register haritası GridSentinel'a aittir; ADM/GDZ register haritası değildir.
