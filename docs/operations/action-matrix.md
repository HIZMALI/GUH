# Otomatik aksiyon politikası

Tek yürütülebilir kaynak `services/anomaly_engine/actions.py`; katalog `GET /api/action-policy`, son değerlendirme `GET /api/panels/{id}` içindeki `actions`. UI aynı sonucu gösterir. Her aksiyon `type`, `trigger`, `automatic`, `status`, `channel`, `description`, `safety_boundary` taşır. Yeni koşunun ilk frame'i gelmeden eski aksiyonlar güncelmiş gibi gösterilmez.

| Tetikleyici | Otomatik yerel işlem | Operatöre öneri | Koruma sınırı |
|---|---|---|---|
| NORMAL | Ölçüm, kalite ve açıklanabilir risk izleme | Normal izleme | Fiziksel komut yok |
| ATTENTION | Dashboard durumu, kalıcı alarm/olay, SCADA alarm bayrağı; SMS/WhatsApp kaydı yok | Eğilimi ve bağlantı koşullarını inceleme | Eşikler mühendislik demo varsayımı |
| WARNING | Dashboard/alarm/SCADA; yeni/yükselen alarmda SMS_MOCK + WHATSAPP_MOCK | Yetkin ekiple bakım değerlendirmesi | Kesici açtırma veya cihaz yazması yok |
| CRITICAL | Yüksek öncelik, escalation, SCADA kritik kodu, mock bildirim | Olay iş akışı ve acil durum değerlendirmesi | İşletmenin onaylı prosedürünü ikame etmez |
| ARC_EVENT | Sentetik ABB dedektör/röle/zaman kaydı, audit, kritik alarm, SCADA ark bayrağı, acil iki mock kanal | Olayı yetkin operasyon ekibi değerlendirir | ABB koruması bağımsızdır; GridSentinel trip/reset üretmez |
| COMMUNICATION_LOSS | Ayrı availability alarmı, stale işareti, SCADA iletişim/sensör bayrağının sıfırlanması | Besleme, gateway, ağ ve sensör bağlantısını inceleme | Son değer güncelmiş gibi sunulmaz |

Katalog sürüm 2: ATTENTION seviyesinde kalıcı alarm ve olay korunur, SMS/WhatsApp mock kaydı üretilmez. İletişim kaybı kullanılabilirlik/bağlantı aksiyonlarıyla ele alınır. WARNING ve CRITICAL seviyelerinde, ayrıca ark olayında iki mock kanal kullanılır. Tekrar gözlem tekrar gönderim değildir. Yeni/yükselen alarmın dışında aynı alarm seviyesi `deduplicated` görünür. `sms_mock` ve `whatsapp_mock` kayıtlarının durumu **simulated**; gerçek servis sağlayıcı çağrısı, telefon alıcısı veya teslim garantisi yoktur.

Operator/admin onayı alarmı silmez: `acknowledged`, audit ve olay kaydı oluşur. Normalleşme `resolved`; yeni demo revision önceki açık alarmları `demo_run_superseded` gerekçesiyle kapatır, geçmişini korur. Demo koşusunun kapanması gerçek sahadaki tehlikenin giderildiği anlamına gelmez.

Kanıt: `tests/unit/test_v2_scheduler_actions.py`, `tests/integration/test_v2_runs.py`, [güncel policy gözlemleri](../verification/v2-frontend-observations.json), [ATTENTION ekranı](../verification/v2-attention-policy.png), [WARNING ekranı](../verification/v2-warning-policy.png), [bildirim ekranı](../verification/v2-notifications.png). Policy ekranları gerçek API yanıtını yalnız tarayıcı çiziminde sabitler; backend çalışmayı sürdürür ve bildirim sayıları canlı API'den doğrulanır. Önceki politika ile üretilmiş tarihsel bildirimler korunur; yeni ATTENTION gözlemlerinde bildirim oluşmaz. MQTT QoS1 ve kalıcı kimlikler uygulama tekrarını engeller; broker power-loss ve uzun saha kopması ayrı saha testidir.

Fleet `open_alarms` yalnız her panonun mevcut demo run kimliğine ait `active` veya `acknowledged` alarmları sayar. Alarm Merkezi tüm tarihsel kayıtları korur; okuma ve filtreleme hiçbir alarmı silmez.
