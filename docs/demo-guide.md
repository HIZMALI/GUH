# Demo rehberi — V2

## Başlangıç
`python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation` ile500 panolu yerel sunumu başlatın. [Operasyon ekranına](http://localhost:3000) `.env` kullanıcı bilgileriyle giriş yapıp PNL-001'i seçin. Tek tık “Termal+PD demosu” veya “Ark demosu” yeni kalıcı koşu başlatır. Eski `python scripts/run_demo.py --scenario combined_thermal_pd` komutu korunur; standart yeni kurulum100 panodur. Filo genişletilir, mevcut kayıtlar küçültülmez/silinmez.

Ekrandaki sentetik veri işareti ve “koruma sistemi değildir” sınırı sunumun parçasıdır. Excel yalnız152 sentetik L1 örneği içerir; diğer kanallar üretilmiştir. Kaynak satırı ve kanal kökeni API'de korunur. Replay15 dakikalık kaynak aralığını hızlandırır; grafik zamanı saha tarihi değildir. V2'de tek focus1,5s, kalan499 pano yaklaşık10,115s aralıkla raporlar; toplam yayın tavanı50frame/s korunur. Focus olmadan eski100/3s,250/5s,500/10s tempo aynıdır. Nominal combined kritik31.adım/46,5s; arc8.adım/12s. Gerçek uçtan uca süre [runtime raporunda](verification/v2-runtime.json) ölçülür; hedef≤75s/≤20s. Lead yalnız sentetik adım farkıdır, saha öngörü süresi değildir.

Varsayılan grafik “Mevcut demo çalışması”dır. Yeni seçim ilk örneğe kadar bekleme gösterir; önceki kritik değer/aksiyonlar yeni koşuya taşınmaz. “Tüm geçmiş”, V1'in run kimliği olmayan kayıtları dahil, sayfalı geçmişi açar. Alarmlar güncel/tüm, durum ve önem derecesine göre filtrelenir. Yeni revision eski açık alarmı `demo_run_superseded` gerekçesiyle kapatır; telemetri, olay, bildirim ve audit korunur.

[Beş dakikalık final metni](final-demo-script.md), [jüri listesi](jury-checklist.md), [tek aksiyon politikası](operations/action-matrix.md). Yaygınlaştırma ekranında ölçülmüş ölçek tablosu, paketler, A/B/C, yenilik ve boş girdide fiyat üretmeyen TCO vardır. H1 sağ yardımcı TH-A hava alanındadır. SCADA500 panoyu1502/1503/1504 banklarında sunar; PNL500 bank3/unit6. Kaynak MPR/TVOC haritalarıyla prototipe ait output map ayrı gösterilir.

## Beş dakikalık sunum akışı
1. **Filo**: toplam pano, severity dağılımı, haberleşme ve sıralı risk. Bölge/trafo filtresinden tek panoya inin.
2. **Pano**: kaynak çizime dayalı 1600×1500×450 mm yerleşim; sıcaklık, nem, HFCT/acquisition, Arc Guard, analizör ve gateway noktalarını seçin. Bunlar önerilen saha konumlarıdır.
3. **Termal + PD**: senaryoyu başlatın. Başlangıç yaklaşık health96/risk8; termal artış, yükle uyuşmazlık ve PD yükselmesi açıklamaya eklenir. NORMAL → ATTENTION → WARNING → ileri aşamada CRITICAL. Katkı puanları ve önerilen operatör aksiyonunu okuyun; bu bir arıza teşhisi veya açma komutu değildir.
4. **Ayrı ark olayı**: `arc_event` seçin. Detector X1:3/X2:6, trip K4 ve timestamp simülasyonu görünür. GridSentinel sertifikalı cihazdan gelmesi beklenen olayı gösterir; kesiciye komut vermez.
5. **SCADA ve bildirim**: Modbus master ekranını açın. Risk, health ve alarm register'ları gerçek yerel TCP okumasıyla güncellenir. Bildirimler `simulated`, alıcı demo operasyon grubudur. Alarmı onaylayın; audit ve history saklanır.
6. **İletişim/sensör arızası**: `communication_loss` önce Arc Guard linkini, sonra gateway akışını kaybeder; durum healthy gibi kalmaz. `sensor_failure` eksik/imkânsız/stuck değerleri gösterir.

## Senaryolar
API `/api/scenarios`, dosyalar `data/scenarios/`, generator `services/simulator/scenarios.py`. Senaryo seçiminde ilgili pano revision değişir ve simulator adım0'dan başlar. Başlangıç/alarm/zaman çizelgesi senaryo belgelerinde kayıtlıdır. Demo reset fiziksel cihaza yazmaz; sentetik akışı normal başlangıca çeker, geçmiş/audit korunur.

CLI'den sadece senaryo değiştirme:

```powershell
python scripts/run_demo.py --connect-only --scenario arc_event
python scripts/run_demo.py --connect-only --scenario sensor_failure
python scripts/run_demo.py --connect-only --scenario communication_loss
```

## Doğrulama
`python -m scripts.verify_v2_runtime` gerçek500 panolu focused süre/clean history/üç bank kanıtını yazar. `python scripts/verify_stack.py --restarts --output docs/verification/v2-stack.json` API/PostgreSQL/MQTT kesintisini oluşturup geri getirir. V1 kanıtını korumak için yeni çıktı adı kullanın. Bunları ve E2E'yi aynı anda veya sunum sırasında çalıştırmayın; PNL001 senaryoları değişir.

Python testleri: `docker compose exec api python -m pytest tests/unit tests/integration tests/modbus tests/source -q`. E2E: `apps/web` içinde `npm run test:e2e`. Tam ölçüm komutları ve sınırları `performance.md` içinde.
