# GridSentinel V2

Grid Up Hackathon için AG panoda kritik duruma giden elektriksel, termal, nem ve PD belirtilerini birlikte izleyen **şirket içi condition-monitoring ve karar destek prototipi**. Mevcut MPR/ABB yatırımını yeniden kullanır; açıklanabilir kurallar, veri kalitesi ve kalıcı erken uyarı zaman çizelgesiyle operatöre riskin nedenini ve önerilen aksiyonu gösterir.

**Demo verileri sentetiktir. GridSentinel koruma rölesi değildir.** Gerçek pano kurulumu, gerçek ADM/GDZ SCADA bağlantısı veya SMS/WhatsApp gönderimi yapılmaz.

Gerçekte çalışan zincir: 500 sanal pano → kimlik doğrulamalı MQTT → FastAPI/PostgreSQL → alarm/audit/mock bildirim → Next.js → üç banklı salt okunur Modbus TCP. Tek seçili demo hızlanırken 499 pano veri gönderir. Yeni koşu grafikleri temiz başlar; eski kayıtlar silinmez. Retrofit kartın pin/net/bağlantı dosyaları, host üzerinde test edilen C++ firmware çekirdeği ve A/B/C kurulum planı saha yaklaşımını somutlaştırır. CORE/THERMAL/ADVANCED PD paketleri mevcut cihazları korur; TCO yalnız kullanıcı girdileriyle hesaplanır. Yenilik; çoklu sinyal, açıklanabilir karar, veri kökeni ve yerel SCADA'nın tek akışta birleşmesidir.

## Tek komutla çalıştır

Docker Linux engine ve Python 3.10+ hazırken repo kökünde:

```powershell
python scripts/run_demo.py --scenario combined_thermal_pd
```

500 panolu jüri sunumu:

```powershell
python scripts/run_demo.py --presentation --panels 500 --scenario normal_operation
```

PNL-001'i açıp **Termal+PD demosu** veya **Ark demosu** düğmesine basın. Son yerel ölçümde combined **47,687 s**, arc **13,368 s**; erken uyarı kritik seviyeden **10 sentetik adım** önce oluştu. Bu hızlandırılmış süreler saha arıza tahmin süresi değildir. [5 dakikalık sunum metni](docs/final-demo-script.md).

[Dashboard: localhost:3000](http://localhost:3000). İlk çalıştırmada `.env` içinde rastgele yerel parolalar oluşturulur. `ADMIN_USERNAME` / `ADMIN_PASSWORD` ile giriş yapın. Sonraki başlatmalar için `docker compose up -d`; durdurmak için `docker compose stop`. Ayrıntılar [kurulum rehberinde](docs/install-guide.md).

## Çalışan kapsam

- Next.js/TypeScript operasyon ekranı: filo, bölge/trafo/pano detayı, kaynak çizime dayalı tıklanabilir şema, trend ve risk açıklamaları.
- FastAPI, PostgreSQL ve kimlik doğrulamalı Mosquitto; sentetik MQTT simulator ve 152 satırlık orijinal L1 replay.
- Açıklanabilir kurallar/trendler, kalite/iletişim problemleri, alarm yaşam döngüsü ve açıkça simüle bildirimler.
- Kaynak PDF'lere dayalı salt okunur MPR-53CS ve TVOC-2 decoder'ları; ayrı gerçek yerel Modbus TCP bridge ve SCADA master.
- 10 senaryo; 100/250/500 panel için tekrar çalıştırılabilir yük testi, Python ve tarayıcı testleri.
- Somut EDA bağımsız [carrier kart](hardware/pcb/README.md), pin/netlist/güç/yerleşim dosyaları; [referans MCU kaynak kodu](edge/firmware/README.md), RF ve A/B/C müdahale planı.
- Current-run/tüm geçmiş, ölçülebilir erken uyarı, merkezi aksiyon politikası, alarm filtreleri ve **Yaygınlaştırma** ekranında gerçek ölçüm/paket/TCO karşılaştırması.

SCADA: PNL-001–247 port 1502, PNL-248–494 port 1503, PNL-495–500 port 1504. PNL-500 **bank 3 / unit 6**, gerçek yerel TCP okumasıyla doğrulandı. MPR/TVOC kaynak haritaları verilen dokümanlardan uygulanmıştır; GridSentinel output map'i prototipe aittir, ADM/GDZ resmî haritası değildir. [Register ve yapılandırma](docs/scada/register-map.md).

## Kaynaklar ve sınırlar

Verilen PDF/Excel dosyaları değiştirilmez. [Kaynak analizi](docs/source-analysis.md), Excel'de hangi verilerin bulunduğunu ve teknik adres/yerleşim dayanaklarını açıklar. Excel yalnız L1 sentetik akım içerir; diğer kanalların üretimi API/UI üzerinde etiketlidir. PD acquisition zinciri konsepttir; sentetik feature'lar kalibre gerçek PD ölçümü değildir. RF kapsama/pil ömrü, gerçek Modbus word order ve saha alarm eşikleri doğrulanmış değildir.

Teknik mimari [MASTER_SPEC.md](MASTER_SPEC.md) ve [architecture.md](docs/architecture.md); takım kuralları [AGENTS.md](AGENTS.md). Üretim/saha güvenlik sınırları [security.md](docs/security.md), kurulum kesintileri [installation-matrix.md](docs/installation-matrix.md), kablosuz seçimi [wireless-design.md](docs/wireless-design.md).

## Demo ve doğrulama

[Demo akışı](docs/demo-guide.md), [V2 makine özeti](docs/verification/v2-summary.json), [performans](docs/performance.md) ve [kabul matrisi](docs/acceptance.md) gerçek sonuçları ve tekrar komutlarını içerir. Değişiklik öncesi temiz V1 commit'inde 62 Python, 7 tarayıcı, 11 servis/kesinti ve 6 yük vakası yeniden geçti; 6800/6800 commit kaydı saklandı. V2: **host 104 PASS, container 104 PASS, Chromium 13 PASS, servis/kesinti 11 PASS**; C++ host çekirdeği 308 kontrol ve TCO 5 sınır testi PASS. 100/250/500 HTTP+MQTT testlerinde **6.800/6.800 kalıcı commit** doğrulandı; yeni kanıtlar ayrı dosyalardadır. PostgreSQL geçişinde **237.402 eski telemetri kaydının içerik özeti birebir korundu**. [Geçiş kanıtı](docs/verification/v2-legacy-preservation.json).

```powershell
python -m pytest -q
python -m scripts.verify_v2_runtime
python scripts/verify_stack.py --restarts --output docs/verification/v2-stack.json
```

Frontend `apps/web` içinde `npm run test:unit` ve `npm run test:e2e:v2`; eski `npm run test:e2e` korunur. Senaryo/E2E/kesinti/yük testleri aynı anda çalıştırılmaz. Sırlar Git'e alınmaz. Runtime public cloud bağımlılığı yoktur; ilk paket/image indirmesi kurulum aşamasıdır. Çevrimdışı image aktarımı [deployment.md](docs/deployment.md).

## Teslim ve sınırlar

[Gereksinim izlenebilirliği](docs/requirements-traceability.md), [jüri listesi](docs/jury-checklist.md), [maliyet/fayda](docs/cost-benefit.md), [yenilikçilik](docs/innovation.md), [çevresel/EMC planı](docs/hardware/environmental-emc-plan.md), [aksiyon matrisi](docs/operations/action-matrix.md).

Hafif delta: `handoff/GridSentinel-v2-delta.zip`; temel commit `4a0f4c1cae879604a384e91862749fef754abecc`. Değişen/yeni dosyalar, Git binary patch ve V2 kanıtlarını içerir. `.env`, bağımlılıklar, cache, volume ve değişmeyen PDF/Excel dahil değildir. [Tekrar paketleme](scripts/package_v2_delta.py) gerçek Git index'ini değiştirmeden patch uygulanabilirliğini ve sır taramasını doğrular.

Kart üretilmedi; EDA-neutral çizimler yönlendirilmiş/sertifikalı PCB değildir. C++ **host** derleme/testi, ESP32 hedef derleme/flash değildir; embedded build **NOT_RUN**, KiCad ERC/DRC **NOT_RUN**. Fiziksel UART/BLE/Ethernet/kalıcı depolama/watchdog/MQTT adapter implementasyonu, canlı firmware verisini API’ye dönüştürecek normalizer ve saha commissioning’i henüz yapılmadı. RF, pil ömrü, kalibre PD, EMC/IP ve gerçek maliyet/ROI doğrulanmadı. Yerel ölçümler kısa burst'tür; tek API süreci kullanılır, uzun soak ve çoklu worker desteği ayrıca gerekir.
