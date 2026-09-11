"""Explainable demonstration rules; thresholds are assumptions, not protection settings."""
from statistics import median

STATE_ORDER = {'NORMAL': 0, 'ATTENTION': 1, 'WARNING': 2, 'CRITICAL': 3}
MAIN_INCOMER_REFERENCE_A = 2312
ASSUMPTIONS = [
    'Eşikler demo için yapılan mühendislik varsayımlarıdır; evrensel cihaz sınırları veya koruma ayarları değildir.',
    'Akımın ana girişten izlendiği varsayılır ve kaynak belgede belirtilen 2312 A ana bara anma akımı kullanılır. Excel dosyasındaki sensör oranları, çıkış devrelerinin anma akımı değildir.',
    'PD göstergeleri kalibrasyonsuz, göreli birimlerle sentetik olarak üretilir; kalibre edilmiş pC ölçümü yapılmaz.',
    'Eğilim hesabında son 12 kabul edilmiş telemetri kaydına kadar veri kullanılır. Hızlandırılmış demo zamanı ayrıca belirtilir.',
]
CHANNEL_LABELS = {
    'current_l1': 'L1 akımı', 'current_l2': 'L2 akımı', 'current_l3': 'L3 akımı',
    'current_neutral': 'Nötr akımı', 'voltage_l1': 'L1 gerilimi', 'voltage_l2': 'L2 gerilimi',
    'voltage_l3': 'L3 gerilimi', 'active_power_kw': 'Aktif güç', 'reactive_power_kvar': 'Reaktif güç',
    'apparent_power_kva': 'Görünür güç', 'power_factor': 'Güç faktörü', 'frequency_hz': 'Frekans',
    'thd_current': 'Akım THD', 'thd_voltage': 'Gerilim THD', 'temperature_c': 'Bağlantı sıcaklığı',
    'ambient_temperature_c': 'Ortam sıcaklığı', 'humidity_pct': 'Bağıl nem',
    'pd_pulse_count': 'PD darbe sayısı', 'pd_peak': 'PD tepe değeri', 'pd_rms': 'PD RMS değeri',
    'pd_activity_rate': 'PD aktivite hızı', 'pd_baseline_ratio': 'PD referans oranı', 'battery_pct': 'Pil seviyesi',
}
QUALITY_LABELS = {'missing': 'veri eksik', 'invalid': 'geçersiz ölçüm', 'stuck': 'değer takılı kalmış', 'stale': 'veri güncel değil'}

def state_for(score: float) -> str:
    return 'CRITICAL' if score >= 80 else 'WARNING' if score >= 45 else 'ATTENTION' if score >= 20 else 'NORMAL'

def evaluate(measurements: dict, quality: dict, arc: dict, communication_ok: bool,
             history: list[dict] | None = None) -> dict:
    history = history or []
    points = [{'rule': 'baseline', 'points': 8, 'detail': 'Sentetik demonun başlangıç değerleri: risk 8 / sağlık 96.'}]
    observed, data_quality = [], []

    def good(name):
        return measurements.get(name) if quality.get(name) == 'good' else None

    def add(rule, value, detail):
        if value:
            points.append({'rule': rule, 'points': value, 'detail': detail})
            observed.append(detail)

    temperature = good('temperature_c')
    humidity = good('humidity_pct')
    pd_ratio = good('pd_baseline_ratio')
    currents = [good(k) for k in ('current_l1', 'current_l2', 'current_l3')]
    load = max(currents) if all(x is not None for x in currents) else None
    if temperature is not None:
        add('temperature', 45 if temperature >= 80 else 30 if temperature >= 65 else 15 if temperature >= 55 else 0,
            f'Bağlantı sıcaklığı {temperature:.1f} °C; demo eşikleri 55 / 65 / 80 °C.')
    if humidity is not None:
        add('humidity', 40 if humidity >= 95 else 28 if humidity >= 85 else 15 if humidity >= 75 else 0,
            f'Bağıl nem %{humidity:.1f}; demo eşikleri %75 / %85 / %95.')
    if pd_ratio is not None:
        add('pd_activity', 42 if pd_ratio >= 5 else 30 if pd_ratio >= 3 else 17 if pd_ratio >= 1.8 else 0,
            f'Sentetik PD aktivitesi referansın {pd_ratio:.2f} katı; bu gösterge kalibre edilmemiştir.')
    if load is not None:
        ratio = load / MAIN_INCOMER_REFERENCE_A
        add('load', 42 if ratio >= 1.2 else 25 if ratio >= 1 else 12 if ratio >= .95 else 0,
            f'En yüksek faz akımı {load:.1f} A; kaynak belgedeki ana bara referansı {MAIN_INCOMER_REFERENCE_A} A. Akımın ana girişten izlendiği varsayılır.')
        mean = sum(currents) / 3
        imbalance = (max(currents) - min(currents)) / mean if mean else 0
        add('phase_imbalance', 20 if imbalance >= .20 else 10 if imbalance >= .12 else 0,
            f'Faz akımları arasındaki fark, ortalama akımın %{imbalance * 100:.1f} değerinde.')
    frequency = good('frequency_hz')
    if frequency is not None:
        add('frequency', 15 if frequency < 49 or frequency > 51 else 0,
            f'Frekans {frequency:.2f} Hz; demo için varsayılan 49–51 Hz aralığının dışında.')
    thd = good('thd_current')
    if thd is not None:
        add('current_thd', 12 if thd >= 20 else 0, f'Akım THD değeri %{thd:.1f}; demo eşiği %20.')

    baseline_temperatures = [h['measurements'].get('temperature_c') for h in history
                             if h.get('quality', {}).get('temperature_c', 'good') == 'good'
                             and h.get('measurements', {}).get('temperature_c') is not None]
    trend = {}
    if temperature is not None and len(baseline_temperatures) >= 3:
        baseline = median(baseline_temperatures)
        rise = temperature - baseline
        ewma = baseline_temperatures[0]
        for value in baseline_temperatures[1:] + [temperature]:
            ewma = .3 * value + .7 * ewma
        mad = median(abs(v - baseline) for v in baseline_temperatures)
        robust_z = .6745 * (temperature - baseline) / max(mad, .5)
        trend = {'temperature_moving_median_c': round(baseline, 2), 'temperature_ewma_c': round(ewma, 2),
                 'temperature_delta_c': round(rise, 2), 'temperature_robust_z': round(robust_z, 2),
                 'window_frames': len(baseline_temperatures)}
        add('thermal_trend', 12 if rise >= 12 else 6 if rise >= 6 else 0,
            f'Sıcaklık, kabul edilmiş son {len(baseline_temperatures)} kaydın hareketli medyanına göre {rise:.1f} °C arttı.')
        baseline_loads = [h['measurements'].get('current_l1') for h in history
                          if h.get('measurements', {}).get('current_l1') is not None
                          and h.get('quality', {}).get('current_l1', 'good') == 'good']
        if load is not None and baseline_loads and median(baseline_loads) > 0:
            load_change = abs(currents[0] / median(baseline_loads) - 1)
            add('thermal_load_correlation', 12 if rise >= 8 and load_change < .15 else 0,
                f'Sıcaklık {rise:.1f} °C artarken L1 yükü %{load_change * 100:.1f} değişti. Gevşek bağlantı olasılığı bir varsayımdır, kesin tanı değildir.')
    if temperature is not None and pd_ratio is not None:
        add('thermal_pd_correlation', 12 if temperature >= 55 and pd_ratio >= 1.8 else 0,
            'Sıcaklık ve sentetik PD aktivitesi birlikte yükseliyor; yalıtım ve bağlantılar incelenmeli.')

    for name, q in quality.items():
        if q != 'good':
            data_quality.append(f'{CHANNEL_LABELS.get(name, name)}: {QUALITY_LABELS.get(q, q)}')
    if not communication_ok:
        data_quality.append('Ağ geçidiyle iletişim yok veya veri güncelliğini yitirmiş; gösterilen son değerler canlı ölçüm değildir.')
    if not arc.get('communication_ok', True):
        data_quality.append('Arc Guard iletişimi, ağ geçidinin durumundan bağımsız olarak kesilmiş.')
    if arc.get('active_errors'):
        data_quality.append(f'Arc Guard tanılama hata kodları: {arc["active_errors"]}')
    score = min(100, sum(p['points'] for p in points))
    if data_quality:
        floor = 45 if not communication_ok else 20
        if score < floor:
            add('availability', floor - score, f'Veri kalitesi veya erişilebilirlik sorunu nedeniyle risk en az {floor} olarak gösterilir; değerlendirmeye duyulan güven azalır.')
            score = floor
    if arc.get('event'):
        add('arc_event', max(0, 100 - score), 'Sentetik ABB TVOC-2 olay bilgisi alındı. Sertifikalı koruma cihazı bağımsız çalışmayı sürdürür.')
        score = 100
    quality_penalty = min(75, len([q for q in quality.values() if q != 'good']) * 6)
    if not arc.get('communication_ok', True):
        quality_penalty += 20
    if arc.get('active_errors'):
        quality_penalty += 10
    health = max(0, round(96 - .65 * (score - 8) - quality_penalty)) if communication_ok else 0
    rules = {p['rule'] for p in points}
    cause = ('ABB Arc Guard için üretilmiş sentetik olay.' if arc.get('event') else
             'İletişim veya sensör verisine erişim sorunu var; ekipmanın durumu doğrulanamıyor.' if data_quality else
             'Gevşek bağlantı veya yalıtım bozulması olasılığı var. Göstergelerin birlikte değişmesi kesin tanı oluşturmaz.' if rules & {'thermal_pd_correlation', 'thermal_load_correlation'} else
             'Demo için kullanılan mühendislik varsayımlarına göre izlenen göstergeler yükselmiş.' if score >= 20 else
             'Sentetik çalışma verileri beklenen referans aralığında.')
    action = ('Sahanın acil durum prosedürlerini izleyin ve sertifikalı koruma cihazının olay kayıtlarını inceleyin. Uzaktan açtırma veya sıfırlama komutu verilmez.' if arc.get('event') else
              'Ağ geçidini, sensör beslemesini, zaman damgalarını ve iletişimi kontrol ederek güvenilir veri akışını yeniden sağlayın.' if data_quality else
              'Uygun bir bakım döneminde bağlantıların, yükün ve yalıtımın yetkin personel tarafından incelenmesini planlayın.' if score >= 20 else
              'İzlemeyi sürdürün ve ölçümleri normal çalışma referansıyla karşılaştırın.')
    return {'risk_score': round(score), 'health_score': health, 'state': state_for(score),
            'sensor_health': max(0, 100 - quality_penalty) if communication_ok else 0,
            'confidence': max(0, 100 - quality_penalty) if communication_ok else 0,
            'explanation': {'observed': observed or ['Sentetik ölçümler demo referans aralığında.'],
                            'possible_cause': cause, 'recommended_action': action, 'contributions': points,
                            'data_quality': data_quality, 'assumptions': ASSUMPTIONS, 'trend': trend}}
