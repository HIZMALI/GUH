# Yerel Demo Rehberi

## Başlatma

500 sanal pano ve normal başlangıç durumu için:

```powershell
python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation
```

[Operasyon ekranı](http://localhost:3000) yerel `.env` kullanıcı bilgileriyle erişilir. PNL-001 odak demo panelidir. Arayüzdeki Termal+PD ve Ark senaryoları yeni bir kalıcı koşu başlatır. `python scripts/run_demo.py --scenario combined_thermal_pd` komutu da desteklenir; standart yeni kurulum 100 panodur. Filo genişletilir, mevcut kayıtlar silinmez.

## Veri ve zaman modeli

Kaynak workbook 152 sentetik L1 örneği içerir; diğer ölçüm kanalları üretilmiştir. Kaynak satırı ve kanal kökeni API'de korunur. Replay, 15 dakikalık kaynak aralığını hızlandırır; grafik zamanı saha tarihi değildir.

Odak pano 1,5 saniyelik sentetik adımlarla, diğer 499 pano yaklaşık 10,115 saniyelik aralıklarla raporlar. Toplam yayın tavanı 50 frame/s'dir. Odak pano bulunmadığında 100/3 s, 250/5 s ve 500/10 s tempo kullanılır. Birleşik senaryoda kritik adım 31, ark olayında adım 8'dir; doğrulanan uçtan uca süreler [runtime raporunda](verification/v2-runtime.json) bulunur.

## Güncel koşu ve geçmiş

Varsayılan grafik “Mevcut demo çalışması”dır. Yeni seçimde ilk örnek beklenirken önceki kritik değerler yeni koşunun ölçümü olarak gösterilmez. “Tüm geçmiş”, run kimliği olmayan V1 kayıtları dahil sayfalı geçmişi açar. Alarm filtreleri koşu, durum ve önem derecesini kapsar.

Yeni revision, önceki açık alarmı `demo_run_superseded` gerekçesiyle kapatır; telemetri, olay, bildirim ve audit korunur. Fleet açık alarm sayısı yalnız her panonun güncel koşusundaki active/acknowledged alarmları kapsar.

## Senaryo ve ekran kapsamı

| Görünüm / senaryo | Gözlenebilir davranış |
|---|---|
| Filo ve pano | Hiyerarşi, haberleşme, risk sıralaması ve kaynak çizime dayalı izleme noktaları |
| `combined_thermal_pd` | Termal/PD katkıları, NORMAL → ATTENTION → WARNING → CRITICAL geçişleri ve öneriler |
| `arc_event` | TVOC dedektör/röle/zaman simülasyonu, acil mock bildirim ve audit |
| `communication_loss` | Arc Guard bağlantısı ve gateway akışındaki kaybın ayrı görünmesi |
| `sensor_failure` | Eksik, imkânsız veya sabitlenmiş sensör değerlerinin kalite işaretleri |
| SCADA | Üç bankta salt okunur gerçek yerel TCP; PNL-500 bank 3 / unit 6 |
| Yaygınlaştırma | Ölçek kanıtları, paketler, A/B/C ve eksik girdide fiyat üretmeyen TCO |

On senaryonun tamamı `/api/scenarios` ve `data/scenarios/` altında tanımlıdır. Seçim, ilgili panonun revision değerini değiştirir; simulator adım 0'dan başlar. Demo reset fiziksel cihaza yazmaz; sentetik akışı normal başlangıca alır ve geçmişi korur. [Ayrıntılı demo akışı](demo-walkthrough.md), [aksiyon politikası](operations/action-matrix.md).

## Komut satırından senaryo seçimi

```powershell
python scripts/run_demo.py --connect-only --scenario arc_event
python scripts/run_demo.py --connect-only --scenario sensor_failure
python scripts/run_demo.py --connect-only --scenario communication_loss
```

## Doğrulamayı yeniden üretme

`python -m scripts.verify_v2_runtime` odak pano süresini, koşu/geçmiş ayrımını ve üç bankı sınar. `python scripts/verify_stack.py --restarts --output docs/verification/v2-stack.json` API/PostgreSQL/MQTT kesinti ve toparlanma kontrollerini çalıştırır. Bu kontroller senaryo veya servis durumunu değiştirdiğinden E2E ve yük testleriyle eşzamanlı yürütülmez. Tarihli kanıtların korunması için ayrı çıktı yolları kullanılır.

Güncel checkout test komutu `python -m pytest -q -k "not test_all_sources_have_hashes_without_changing_originals"`; harici kaynak kontrolünün koşulları [kaynak analizinde](source-analysis.md#kaynak-dosyalarının-dağıtımı-ve-hash-kontrolü) açıklanır. Frontend için `apps/web` içinde `npm run test:unit` ve `npm run test:e2e:v2` kullanılır. Yük yöntemi ve komutları [performans raporunda](performance.md#testi-yeniden-üretme) bulunur.
