# 1600 kVA pano için önerilen izleme noktaları

Kaynak `AG Pano Teknik Çizim-1600kVA.pdf`, tek sayfa/basılı s.51, EK-II/14: dahili1250–1600kVA pano. **A=1600mm (+100/-0), B=1500mm (+100/-0), C=450mm (+50/-0). Alt kablo bağlantı alanı en az400mm.** Kaynaktaki üst giriş baraları/CT, sol kompanzasyon, sağ yardımcı/ölçü bölmesi ve ortadaki DSYA çıkış bankası korunur. Kaynak ölçülerle şematik konsept `hardware/concept/panel-placement.svg`.

`1600kVA AG Pano Teknik Özellikleri.pdf` basılı s.34 Tablo8: ana bara2×(100×10mm²), CT2500/5, beş250A + beş400A çıkış ve iki yedek. Ana giriş2312A anma değeri TEDAŞ şartnamesindendir. Excel'deki6000 çarpanlı örnek CT, ana giriş CT'si değildir. MPR mevcut CT/VT'yi okur; sırf radyo kullanmak için ana akım ölçümü yeniden tasarlanmaz.

| Nokta | Önerilen konum | Kaynak / yeni öneri | Yerleşim sınırı |
|---|---|---|---|
| T1–T3 | Üst giriş/CT bölgesindeki uygun bağlantıların sıcaklık gözlemi | Yeni retrofit önerisi | Gerilim sınıfı/izolasyonu uygun yüzey sensörü veya uygun temassız alternatif; canlı iletkene rastgele yapıştırma yok; sınıfC |
| T4–T6 | Riskli seçilmiş DSYA çıkış terminal noktaları | Yeni öneri | Kaynaktaki185mm terminal geometrisi ve servis mesafeleri korunur; tüm12 çıkış ilk BOM'da sensörlü değildir |
| TH-A | Sağ yardımcı bölmedeki temsil edici hava noktası | Yeni sıcaklık/nem düğümü | Bara sıcaklığını ölçmez; duvar/PSU sıcaklığından etkilenmeyecek yer; hava dolaşımı incelemesi gerekir |
| MPR | Sağ ölçü bölgesi | Mevcut ekipmandan veri alınması önerisi | Çizimde her model etiketi yok; MPR-53CS'nin burada fiziksel kurulu olduğu iddiası yok |
| EG | Sağ yardımcı alan / dış izleme kutusu | Yeni gateway ve izole besleme | Mevcut ekipman, kapak hareketi, DIN boşluğu ve termal kapasite yerinde doğrulanır |
| PD-A | Alt kablo bölgesindeki uygun sistem toprak bağlantısı | Kaynağa dayalı HFCT uygulama yeri; yeni acquisition önerisi | Toprak sürekliliğini bozacak işlem yalnız planlı kesinti/prosedür;30/50mm iç çap kontrolü; alt en az400mm net alan korunur |
| ARC-Z1/Z2/Z3 | Üst giriş, çıkış bankası ve kablo bölgeleri için kavramsal kapsama | ABB koruma tasarımını değiştirmeyen izleme zon etiketleri | Fiziksel optik detector sayısı/konumu bu çizimden sertifikalandırılamaz; ABB/site protection mühendisliği onayı gerekir |

Şemadaki nokta koordinatları UI ve konsept amaçlıdır, üretim delik ölçüsü değildir. Metal yüzeyde radyo sensör montajı için saha radyo deneyi gerekir. Dış anten gerektiğinde yalnız yetkili enclosure geçişi ve IP korumasıyla tasarlanır. Form2B ayırma, dokunma koruması, kaçak mesafe, servis erişimi ve kapak hareketi ek parçalarla bozulmaz.

TEDAŞ şartnamesi PDF s.5/basılı4 genel koşullarında maksimum40°C,24s ortalama35°C, dahili alt sınır−5°C; dahili kirlilikII, hariciIII. Dahili IP2X, harici IP54 s.8/basılı7'de. Bu ortam sınırları **pano bağlantısı alarm eşiği değildir**; demo55/65/80°C kuralları bağımsız mühendislik varsayımıdır. Yükseklik, nem, yoğuşma, kirlenme ve kabinetin iç sıcaklık artışı son ürün seçimi öncesinde incelenir.
