# GridSentinel Edge Interface Carrier v0.1

**EDA-neutral referans kart tasarımı; üretim kartı değildir.** 24 VDC yardımcı beslemeden çalışan ESP32-S3 sınıfı MCU, harici Ethernet modülü, iki ayrı izole RS485 portu, yerel radyo, watchdog ve kalıcı tampon arayüzünü pin/net seviyesinde tanımlar. Şebeke/baraya giriş, röle, kesici kumanda veya TVOC reset çıkışı içermez.

| Çıktı | İçerik |
|---|---|
| [schematic.svg](schematic.svg) | Güç ağacı, MCU pinleri, iki izole domain ve dış bağlantılar |
| [pcb-placement.svg](pcb-placement.svg) | Varsayılan 160 × 100 mm zarf içinde yerleşim; yönlendirilmiş PCB değildir |
| [connectors.csv](connectors.csv) | J1–J7: 31 pin / bağlantı ve kullanım sınırları |
| [netlist.csv](netlist.csv) | 199 düğüm; pin, net, domain, kaynak ve seçim durumu |
| [component-selection.md](component-selection.md) | Doğrulanan aday datasheet'leri ve henüz seçilmemiş parçalar |
| [power-budget.csv](power-budget.csv) | Ölçülmemiş yük tahsisi ve varsayılan dönüşüm verimleri |
| [design-rules.md](design-rules.md) | Üretim öncesi koordinasyon ve inceleme kuralları |
| [safety-boundaries.md](safety-boundaries.md) | Yardımcı düşük gerilim / koruma bağımsızlığı sınırı |

2026-09-11 envanterinde `kicad-cli`, KiCad GUI/eeschema/pcbnew bulunmadı. Bu nedenle `.kicad_sch` / `.kicad_pcb` dosyası üretilmedi; **ERC/DRC NOT_RUN**. CSV doğrulaması elektriksel ERC/DRC yerine geçmez. Delik/footprint, bakır yönlendirme, Gerber, üretim BOM'u, creepage/clearance hesabı ve EMC/thermal doğrulama yoktur. Sayısal pinleri seçili adaylara aittir; `_TBD` bileşenlerinde işlevsel uç adları kullanılır ve sahte paket pin numarası verilmez.

Repo kökünden `python hardware/pcb/generate_artifacts.py` CSV/SVG çıktılarını yeniden üretir. `python -m pytest tests/hardware -q` kaynak haritası, pin/domain ve güç bütçesi tutarlılığını kontrol eder. Ayrı gerçek C++ host testi: `python edge/firmware/tools/run_host_tests.py`. Fiziksel kart kurulmadı; tüm demo gözlemleri sentetiktir.
