"""Single on-premise action policy. No action can operate physical protection equipment."""
SAFETY = 'Yalnız izleme ve karar desteği; kesici açtırma, Modbus yazma veya TVOC sıfırlama komutu yoktur.'
MOCK_CHANNELS = ('sms_mock', 'whatsapp_mock')

def action_policy(result, notification_status='eligible'):
    state = result['state']
    arc = result.get('arc', {}).get('event', False)
    unavailable = not result.get('communication_ok', True)
    trigger = 'ARC_EVENT' if arc else 'COMMUNICATION_LOSS' if unavailable else state
    actions = []

    def add(kind, description, automatic=True, status='available', channel=None):
        actions.append({'type': kind, 'trigger': trigger, 'automatic': automatic, 'status': status,
                        'channel': channel, 'description': description, 'safety_boundary': SAFETY})

    add('monitoring', 'Ölçümler, veri kalitesi ve açıklanabilir risk izlenir.', status='active')
    if state != 'NORMAL':
        add('dashboard_state', 'Operasyon ekranındaki risk ve durum göstergeleri güncellenir.')
        add('event_log', 'Durum değişikliği olay geçmişinde kalıcı olarak tutulur.')
        add('persistent_alarm', 'Alarm açılır; onay ve çözülme geçmişi korunur.')
        add('scada_alarm_flag', 'Alarm durumu salt okunur SCADA çıkış haritasında erişilebilir.', channel='modbus_tcp')
        # v1 compatibility: ATTENTION also creates clearly simulated mock records.
        # Repeated accepted frames do not re-send them: runtime applies alarm deduplication.
        for channel in MOCK_CHANNELS:
            add('notification', 'Yerel bildirim kaydı simüle edilir; gerçek sağlayıcıya gönderim yapılmaz.',
                status=notification_status, channel=channel)
        add('operator_recommendation', result['explanation']['recommended_action'], automatic=False, status='recommended')
    if state == 'CRITICAL':
        add('high_priority_alarm', 'Kritik alarm önceliği ve yükseltme kaydı oluşturulur.')
        add('scada_critical_flag', 'Kritik durum kodu salt okunur SCADA haritasında erişilebilir.', channel='modbus_tcp')
        add('incident_workflow', 'Yetkin operasyon ekibinin olay değerlendirmesi önerilir.', automatic=False, status='recommended')
    if arc:
        add('abb_event_ingestion', 'Sentetik ABB dedektör, röle ve olay zaman bilgisi kaydedilir.')
        add('scada_arc_flag', 'Ark olayı bayrağı salt okunur SCADA haritasında erişilebilir.', channel='modbus_tcp')
        add('audit_log', 'Yeni ark olayı denetim izine kaydedilir.')
        add('independent_protection', 'Sertifikalı ABB koruma işlevi GridSentinel dışında bağımsız kalır.', automatic=False, status='external')
    if unavailable or result.get('explanation', {}).get('data_quality'):
        add('availability_alarm', 'İletişim veya sensör verisi sorunu ayrı kullanılabilirlik alarmına dönüşür.')
        if unavailable:
            add('stale_data', 'Son değerler güncel veri olarak sunulmaz; bağlantı sorunu görünür tutulur.')
            add('scada_communication_flag', 'SCADA iletişim ve sensör kullanılabilirliği bayrakları sıfırdır.', channel='modbus_tcp')
        add('connectivity_recommendation', 'Sensör beslemesi, ağ geçidi, zaman damgaları ve iletişim incelenmelidir.',
            automatic=False, status='recommended')
    return actions

def policy_notification_channels(result):
    return [action['channel'] for action in action_policy(result) if action['type'] == 'notification']

def policy_catalog():
    rows = []
    for trigger in ['NORMAL', 'ATTENTION', 'WARNING', 'CRITICAL', 'ARC_EVENT', 'COMMUNICATION_LOSS']:
        result = {'state': 'CRITICAL' if trigger == 'ARC_EVENT' else 'WARNING' if trigger == 'COMMUNICATION_LOSS' else trigger,
                  'communication_ok': trigger != 'COMMUNICATION_LOSS', 'arc': {'event': trigger == 'ARC_EVENT'},
                  'explanation': {'data_quality': [], 'recommended_action': 'Yetkin personelin durum değerlendirmesi önerilir.'}}
        rows.append({'trigger': trigger, 'actions': action_policy(result)})
    return {'version': 1, 'mode': 'synthetic_demo', 'items': rows,
            'note': 'V1 uyumluluğu için ATTENTION seviyesinde de yerel mock bildirim kaydı üretilir. Yeni veya yükselen alarmlar bildirim oluşturur; yinelenen gözlemler gönderimi tekrarlamaz.',
            'safety_boundary': SAFETY}
