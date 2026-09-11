"""Measured transitions within one synthetic run; never a real-field lead-time claim."""

def early_warning_timeline(transitions, complete=False):
    ordered = sorted(transitions, key=lambda item: (item['step'], item['timestamp']))
    first = {}
    for item in ordered:
        first.setdefault(item['state'], item['step'])
    warning, critical = first.get('WARNING'), first.get('CRITICAL')
    lead = critical - warning if warning is not None and critical is not None and warning < critical else None
    if lead is not None:
        status, message = 'demonstrated', f'Erken uyarı, kritik seviyeden {lead} sentetik demo adımı önce oluştu.'
    elif critical is not None:
        status, message = 'critical_without_prior_warning', 'Bu çalışmada kritik durumdan önce WARNING kaydı yok; önceden uyarı süresi iddia edilmez.'
    elif complete:
        status, message = 'no_critical', 'Bu sentetik senaryo kritik seviyeye ulaşmadı; kritik öncesi süre hesaplanmaz.'
    elif warning is not None:
        status, message = 'before_critical', 'Uyarı oluştu; bu çalışmada henüz kritik durum gözlenmedi.'
    else:
        status, message = 'pending', 'Erken uyarı kanıtı için bu çalışmanın durum geçişleri bekleniyor.'
    return {'transitions': ordered, 'warning_step': warning, 'critical_step': critical, 'lead_steps': lead,
            'status': status, 'unit': 'synthetic_demo_steps', 'message': message}
