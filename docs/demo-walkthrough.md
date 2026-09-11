# Demo Akışı

## Demo ortamının amacı

Yerel demo; sentetik cihaz telemetrisinin MQTT üzerinden kalıcı ölçüm, açıklanabilir risk, alarm, operatör ekranı ve salt okunur SCADA verisine dönüşmesini gösterir. Fiziksel saha kurulumu, gerçek ADM/GDZ bağlantısı veya koruma testi değildir. Başlatma ve yapılandırma [demo rehberinde](demo-guide.md) açıklanır.

## Başlangıç durumu

500 sanal pano normal çalışır; PNL-001 odak demo panelidir. Doğrulanan başlangıç durumu **500 NORMAL / 0 offline / 0 güncel açık alarm** değerleridir. Pano görünümü kaynak 1600 kVA AG pano geometrisini kullanır. TH-A/H1, sağ yardımcı devrelerin hava alanında; P1, alt toprak/kablo bölgesindedir. Ek sensör konumları saha yerleşim önerisidir.

Varsayılan grafik güncel demo koşusuna aittir. Yeni koşunun ilk örneği gelene kadar önceki ölçümler güncelmiş gibi gösterilmez. Tüm geçmiş görünümü önceki telemetri, alarm, olay ve audit kayıtlarını erişilebilir tutar.

## Termal + PD senaryosu

`combined_thermal_pd`, yaklaşık sağlık 96 / risk 8 ile başlar. Yükle birlikte sıcaklık ve PD göstergelerinin değişimi, puan katkılarında ve açıklamalarda görünür. PNL-001, 1,5 saniyelik sentetik adımlarla ilerlerken diğer 499 pano veri göndermeye devam eder; toplam yayın tavanı 50 frame/s'dir.

| Durum | Sentetik adım | Gözlenebilir karşılık |
|---|---:|---|
| NORMAL | 0 | İzleme ve başlangıç ölçümleri |
| ATTENTION | 19 | Kalıcı alarm, olay kaydı, SCADA işareti ve operatör önerisi; SMS/WhatsApp yok |
| WARNING | 21 | Uyarı ve bakım önerisi; `sms_mock` ile `whatsapp_mock` kayıtları |
| CRITICAL | 31 | Yüksek öncelikli eskalasyon ve olay inceleme önerisi |

## Erken uyarı

Kalıcı zaman çizelgesi durumun adımını, zamanını, gözlemlerini ve önerisini ilişkilendirir. WARNING ile CRITICAL arasındaki doğrulanmış fark **10 sentetik adımdır**. [Uçtan uca runtime ölçümünde](verification/v2-runtime.json) birleşik senaryo **48,096 s** sürmüştür. Bu süre hızlandırılmış demo zamanıdır; gerçek saha arızasının ne kadar önce tahmin edileceğini göstermez.

## Arc senaryosu

`arc_event`, ABB TVOC olay akışının sentetik örneğidir. Adım 8'de dedektör X1:3/X2:6, trip rölesi K4 ve olay zamanı görünür. Ölçülen yerel süre **13,050 s**'dir. Olay, acil simüle bildirim, SCADA arc işareti ve audit kaydı üretir. ABB koruma işlevi bağımsızdır; GridSentinel kesiciye veya cihaz sıfırlamasına komut göndermez.

## SCADA görünümü

SCADA master ekranı ayrı bridge'den gerçek yerel TCP okumasıyla 12 register alır. PNL-500, bank 3 / iç port 1504 / unit 6 ile adreslenir. Üç bank, 247 + 247 + 6 pano içerir. Host port eşlemeleri [dağıtım belgesinde](deployment.md#windows-host-port-eşlemesi) bulunur.

MPR/TVOC kaynak haritaları ile prototipe ait GridSentinel çıkış haritası birbirinden ayrıdır. Bu çıktı ADM/GDZ'nin resmî register haritası olarak sunulmaz. [Register haritası](scada/register-map.md).

## Yaygınlaştırma ekranı

Yaygınlaştırma görünümü ölçülmüş 100/250/500 cihaz sonuçlarını, CORE/THERMAL/ADVANCED PD kapsamlarını ve A/B/C müdahale sınıflarını bir araya getirir. TCO hesabı kullanıcı girdileriyle çalışır; eksik fiyat alanları sıfır sayılmaz. Geri ödeme hesabı, açık fayda varsayımları ve pozitif net yıllık fayda gerektirir.

Bağlantı kesintisi ve geçersiz sensör verisi ayrı durumlar olarak görünür. Tarihli doğrulama kayıtları belirli test koşullarını belgeler; canlı ekrandaki bağlantı veya kalite uyarılarının yerine geçmez.

İlgili belgeler: [aksiyon matrisi](operations/action-matrix.md), [saha uygulaması](installation-matrix.md), [değerlendirme kapsamı](evaluation-coverage.md), [prototip sınırları](acceptance.md#teknik-sınırlar).
