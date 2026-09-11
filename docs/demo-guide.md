# Demo rehberi

## Başlangıç
`python scripts/run_demo.py --scenario combined_thermal_pd` ile yerel sistemi çalıştırın. [Operasyon ekranına](http://localhost:3000) `.env` içindeki kullanıcı bilgileriyle giriş yapın. Varsayılan100 sanal pano bulunur; site, trafo ve sensör adları demodur. Filo tablosundan PNL-001 seçin.

Ekrandaki sentetik veri işareti ve "koruma sistemi değildir" sınırı sunumun parçasıdır. Sağlanan Excel yalnız L1 akım örneklerini içerir; termal, nem, diğer elektriksel ve PD/ARC kanalları üretilmiştir. Kaynak satırı ve per-channel provenance API'de korunur. Replay15 dakikalık kaynak aralığını hızlandırır. Varsayılan100 panoda3 saniyelik adım; trafik sınırı50frame/s ile250 panoda5s,500 panoda10s. Grafik zamanı demo gözlem zamanıdır, gerçek saha tarihi değildir. Senaryo JSON'undaki saniyeler100 pano/3s örneğidir; büyük filoda aynı adımlar daha uzun sürer. Arc olayı8.adımda,500 panoda yaklaşık80s sonra oluşur.

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
`python scripts/verify_stack.py` gerçek Docker servis health, authentication/RBAC, filo, TCP read/invalid/write rejection ve bildirim kökenini denetler. `python scripts/verify_stack.py --restarts` ek olarak API, PostgreSQL ve MQTT kesintisini oluşturup geri getirir; test kendi oluşturduğu kesintilerin sonunda servisleri yeniden başlatır. Çalışan bir sunum sırasında kullanmayın. JSON sonuçları `docs/verification/` altında tutulur.

Python testleri: `docker compose exec api python -m pytest tests/unit tests/integration tests/modbus tests/source -q`. E2E: `apps/web` içinde `npm run test:e2e`. Tam ölçüm komutları ve sınırları `performance.md` içinde.
