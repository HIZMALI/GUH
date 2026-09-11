# Otomatik aksiyon politikası

Tek yürütülebilir kaynak `services/anomaly_engine/actions.py`; katalog `GET /api/action-policy`, son değerlendirme `GET /api/panels/{id}` içindeki `actions`. UI aynı sonucu gösterir. Her aksiyon `type`, `trigger`, `automatic`, `status`, `channel`, `description`, `safety_boundary` taşır. Yeni koşunun ilk frame'i gelmeden eski aksiyonlar güncelmiş gibi gösterilmez.

| Tetikleyici | Otomatik yerel işlem | Operatöre öneri | Koruma sınırı |
|---|---|---|---|
| NORMAL | Ölçüm, kalite ve açıklanabilir risk izleme | Normal izleme | Fiziksel komut yok |
| ATTENTION | Dashboard durumu, kalıcı alarm/olay, SCADA alarm bayrağı, iki mock kanal kaydı | Eğilimi ve bağlantı koşullarını inceleme | Eşikler mühendislik demo varsayımı |
| WARNING | Aynı kayıt zinciri; yeni/yükselen alarmda bildirim | Yetkin ekiple bakım değerlendirmesi | Kesici açtırma veya cihaz yazması yok |
| CRITICAL | Yüksek öncelik, escalation, SCADA kritik kodu, mock bildirim | Olay iş akışı ve acil durum değerlendirmesi | İşletmenin onaylı prosedürünü ikame etmez |
| ARC_EVENT | Sentetik ABB dedektör/röle/zaman kaydı, audit, kritik alarm, SCADA ark bayrağı | Olayı yetkin operasyon ekibi değerlendirir | ABB koruması bağımsızdır; GridSentinel trip/reset üretmez |
| COMMUNICATION_LOSS | Ayrı availability alarmı, stale işareti, SCADA iletişim/sensör bayrağının sıfırlanması | Besleme, gateway, ağ ve sensör bağlantısını inceleme | Son değer güncelmiş gibi sunulmaz |

V1 davranışını korumak için ATTENTION seviyesinde de yerel mock kayıt oluşur. Tekrar gözlem tekrar gönderim değildir. Yeni/yükselen alarmın dışında aynı alarm seviyesi `deduplicated` görünür. `sms_mock` ve `whatsapp_mock` kayıtlarının durumu **simulated**; gerçek servis sağlayıcı çağrısı, telefon alıcısı veya teslim garantisi yoktur.

Operator/admin onayı alarmı silmez: `acknowledged`, audit ve olay kaydı oluşur. Normalleşme `resolved`; yeni demo revision önceki açık alarmları `demo_run_superseded` gerekçesiyle kapatır, geçmişini korur. Demo koşusunun kapanması gerçek sahadaki tehlikenin giderildiği anlamına gelmez.

Kanıt: `tests/unit/test_v2_scheduler_actions.py`, `tests/integration/test_v2_runs.py`, [gerçek runtime](../verification/v2-runtime.json), [bildirim ekranı](../verification/v2-notifications.png). MQTT QoS1 ve kalıcı kimlikler uygulama tekrarını engeller; broker power-loss ve uzun saha kopması ayrı saha testidir.
