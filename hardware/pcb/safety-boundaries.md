# Değişmez güvenlik sınırları

1. Carrier hiçbir ana bara/şebeke ölçü girişi içermez;24VDC yardımcı kaynak, ayrı izole RS485 ve Ethernet bağlantılarıyla sınırlıdır. MCU'nun güç bütçesi bir mains PSU tasarımı değildir.
2. J1–J7 arasında röle/kesici açtırma, TVOC reset, MPR setpoint veya koruma kumanda terminali yoktur. J6 EN/BOOT ve watchdog yalnız **yerel MCU** içindir. Ethernet RSTn yalnız WIZ850io içindir.
3. RTU çekirdeği yalnız FC03/04 çerçevesi üretir. TVOC213,1000,1100 write adresleri poll planında yoktur. Koruma işlevi ABB ve mevcut bağımsız koruma ekipmanında kalır.
4. J7 ham HFCT giriş değildir. İzolasyon ve acquisition haricen çözülmeden saha kablosu bağlanmaz; aynı güvenli düşük gerilim domain'i şartı sağlanmazsa harici izole interface gerekir. Demo PD feature'ları sentetiktir, kalibre pC değildir.
5. Dışarıdan güvenli mevcut gateway reuse A/B; yeni iç PSU, HFCT, enerjili bağlantıya sensör montajı C sınıfı planlı kesinti/prosedür gerektirir. Sağ yardımcı hacimde ambient sensör erişimi tesis koşuluna göre A/B/C'dir. Kablosuz olması canlı çalışma izni vermez. [Kurulum matrisi](../../docs/installation-matrix.md).
6. Kart üretimi, saha kurulumu, RF kapsama, çevresel/EMC/insulation/termal test ve certified protection değerlendirmesi yapılmadı. Referans adayların datasheet özellikleri tüm assembly'ye taşınmış bir sertifika değildir.
