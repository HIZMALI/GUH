# Maliyet, fayda ve kademeli yaygınlaştırma

Kaynak belgelerde fiyat teklifi veya gerçek saha bakım sonuçları yoktur. Bu model teklif toplamayı ve kapsam karşılaştırmayı destekler; TL/USD fiyatı, tasarruf yüzdesi ya da önlenmiş kesinti süresi iddiası üretmez. Hackathon Proje Konusu s.2–3 maliyet açısından sürdürülebilir, yaygınlaştırılabilir tasarımı; s.5 maliyet/fayda değerlendirmesini ister.

## Üç uygulama seviyesi

| Boyut | CORE | THERMAL | ADVANCED PD |
|---|---|---|---|
| Eklenen donanım | Edge gateway, iki izole arayüz, temel ortam düğümü; mevcut bağlantıya göre güç/kutu | CORE + riskli seçilmiş noktalarda uygun kablosuz yüzey sıcaklık sensörleri | THERMAL + uygun HFCT + geniş bant acquisition/feature katmanı |
| Mevcut yatırımın kullanımı | MPR ölçümleri; varsa TVOC + COM olayları; uygun mevcut gateway | Aynı mevcut cihazlar; akım tekrar ölçülmez | Aynı mevcut cihazlar; varsa mevcut PD acquisition çıktıları |
| Müdahale sınıfı | Güvenli gateway erişimi A/B; yeni iç güç/bağlantı gerekiyorsa C | Canlı bağlantı bölgesine yeni sensör montajı C | HFCT/toprak bölgesi montajı C; hazır feature arayüzüne erişim B olabilir |
| Bakım yükü | Kimlik, bağlantı, yazılım/konfigürasyon, ortam sensörü ve besleme kontrolü | Ek sensör/pil erişimi, bağlantı noktası ve RF kalite takibi | Ayrıca acquisition kalibrasyonu, gürültü değerlendirmesi ve uzman inceleme |
| Kablolama etkisi | Mevcut RS485/LAN'ın kullanımı; yeni güç/arayüz kablosu koşula bağlı | Uygun yerlerde radyo sensörü kablo ekini azaltabilir | HFCT koaksiyel + acquisition beslemesi/LAN; ham MHz sinyal kablosuz ortam sensörüne eşdeğer değildir |
| Göreli karmaşıklık | En az ek ölçüm katmanı | Ek montaj ve RF doğrulaması | En yüksek acquisition/uzmanlık gereksinimi |
| Teklif gerektirenler | Gateway/arayüz, besleme, enclosure, ortam düğümü, keşif ve commissioning | Ek sensör adedi, elektriksel/mekanik uygunluk, güvenli pil değişimi | HFCT modeli/adedi, acquisition, kalibrasyon, uzman devreye alma |
| Hedef kullanım | Elektriksel/çevresel görünürlük ve mevcut ark olaylarının izlenmesi | Bağlantı sıcaklığının yükle birlikte izlenmesinin değerli olduğu panolar | İzolasyon/PD açısından öncelikli, acquisition kurulumunun gerekçelendirildiği sahalar |

CORE kapsamında mevcut TVOC-COM bulunacağı garanti değildir; yeni COM/koruma cihazı gerekli ise ayrı teklif ve yetkili planlı kesinti kapsamıdır. Bir üst seviye otomatik olarak her panoya uygulanmaz. Keşif ve risk önceliği ile seçilmesi, yüksek maliyetli acquisition katmanını tüm filoya zorunlu kılmaz.

## Parametrik TCO

Önce değerlendirme dönemi (yıl), para birimi ve teklif kapsamı belirlenir. Aynı tutar hem gateway paketinde hem ayrı arayüz satırında tekrar sayılmaz. Dashboard bakım ve pil giderlerini **pano başına yıllık** alır ve seçilen yıl sayısıyla çarpar; diğer tutarlar bir defalık yatırımlardır.

```text
Pano başı ilk yatırım = gateway + isolated_interfaces + sensors
                     + installation + commissioning + planned_outage + optional_PD
                     + shared_server / panel_count
Pano başı TCO = ilk yatırım + period_years × (maintenance_annual + battery_annual)
Filo TCO      = panel_count × pano başı TCO
```

Kalemlere KDV/ithalat, ağ güvenliği, kabin tadilatı ve kurum içi iş gücü dahil mi açıkça kaydedilir. MPR/TVOC yeniden satın alınacaksa tutarı mevcut ekipman tekrar kullanımı gibi sıfır varsayılmaz. Opsiyonel PD kullanılmıyorsa kullanıcı bunu açıkça 0 girerek belirtir. Eksik teklif alanı otomatik olarak 0'a dönüştürülmez. `panel_count` pozitif tam sayı olmalıdır.

Dashboard **Yaygınlaştırma** ekranındaki hesaplayıcı kullanıcı girdileriyle çalışır. Varsayılan fiyatlar boştur; tamamlanmamış girdilerle sonuç üretilmez. Sonuç bir fiyat teklifi değildir. Para birimleri çevrilmez; bütün girdiler aynı birimde ve aynı değerlendirme döneminde olmalıdır.

## Fayda nasıl ölçülür?

Beklenen kullanım değeri; farklı sinyallerin birlikte görünmesi, riskin nedeninin operatöre açıklanması, arıza öncesi bakım planlama, merkezden inceleme ve mevcut ekipmanın tekrar kullanılmasıdır. Plansız saha ziyareti veya kesinti azalması bir **potansiyeldir**; sentetik demo bunu ölçmez. Public cloud aboneliği zorunlu değildir, ancak şirket içi sunucu işletiminin maliyeti sıfır değildir.

Bir pilot çalışmada karşılaştırılabilir dönemlerin plansız ziyaret sayısı, bakım bulguları, geçerli/yanlış alarm yükü, operatör inceleme süresi ve gerçekleşen kesinti süreleri kaydedilebilir. Cihaz sayısı, ekipman yaşı ve bakım değişiklikleri kontrol edilmeden farkın tamamı yazılıma atfedilemez.

Hesaplayıcıdaki isteğe bağlı fayda girdileri **pano başına / yıl** varsayımlarıdır: `avoided_hours × outage_hour_cost + avoided_visits × maintenance_visit_cost`. Bunlardan yıllık bakım ve pil maliyeti düşülür. Net fayda pozitifse `pano başı ilk yatırım / net yıllık fayda` basit geri ödeme süresini yıl olarak verir. Boş veya eksik fayda girdilerinde geri ödeme sonucu yoktur; net fayda sıfır/negatifse sonlu bir geri ödeme süresi uydurulmaz. Bütün sayılar kullanıcının varsayımıdır, gerçekleşmiş fayda veya finansal getiri garantisi değildir.

## Neden maliyet açısından sürdürülebilir bir aday?

- MPR ve uygun TVOC-COM verisini kullanmak, aynı elektriksel ölçümü yeniden kurma gereksinimini azaltır.
- Düşük veri hacimli edge arayüzü için MCU sınıfı referans kart, her pano için yüksek maliyetli genel amaçlı bilgisayarı zorunlu kılmaz.
- Ortak merkez sunucusu maliyeti ölçek içinde paylaştırılır; gerçek kapasite ve bakım maliyeti yeniden ölçülür.
- Kablosuz sensör yalnız teknik olarak uygun yerde seçilir. RF başarısızsa gerekli kablolu alternatif bütçeye alınır.
- CORE / THERMAL / ADVANCED PD ayrımı yatırımın saha riskine göre aşamalı yapılmasına izin verir.

Bağlantılar: [BOM](hardware/bom.md), [referans kart](../hardware/pcb/README.md), [kurulum sınıfları](installation-matrix.md), [ölçülmüş ölçek sınırı](performance.md).
