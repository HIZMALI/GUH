# GridSentinel

Grid Up Hackathon için, mevcut Modbus cihazlarını ve önerilen retrofit sensörleri birleştiren şirket içi condition-monitoring prototipi. Elektriksel, termal, çevresel, PD ve Arc Guard göstergelerini ilişkilendirir; operatöre risk puanının nedenini, alarmı ve bakım önerisini gösterir.

**Demo verileri sentetiktir. GridSentinel koruma rölesi değildir.** Gerçek pano kurulumu, gerçek ADM/GDZ SCADA bağlantısı veya SMS/WhatsApp gönderimi yapılmaz.

## Tek komutla çalıştır

Docker Linux engine ve Python3.10+ hazırken repo kökünde:

```powershell
python scripts/run_demo.py --scenario combined_thermal_pd
```

[Dashboard: localhost:3000](http://localhost:3000). İlk çalıştırmada `.env` içinde rastgele yerel parolalar oluşturulur. `ADMIN_USERNAME` / `ADMIN_PASSWORD` ile giriş yapın. Sonraki başlatmalar için `docker compose up -d`; durdurmak için `docker compose stop`. Ayrıntılar [kurulum rehberinde](docs/install-guide.md).

## Çalışan kapsam

- Next.js/TypeScript operasyon ekranı: filo, bölge/trafo/pano detayı, kaynak çizime dayalı tıklanabilir şema, trend ve risk açıklamaları.
- FastAPI, PostgreSQL ve kimlik doğrulamalı Mosquitto; sentetik MQTT simulator ve152 satırlık orijinal L1 replay.
- Açıklanabilir kurallar/trendler, kalite/iletişim problemleri, alarm yaşam döngüsü ve açıkça simüle bildirimler.
- Kaynak PDF'lere dayalı salt okunur MPR-53CS ve TVOC-2 decoder'ları; ayrı gerçek yerel Modbus TCP bridge ve SCADA master.
- 10 senaryo; 100/250/500 panel için tekrar çalıştırılabilir yük testi, Python ve tarayıcı testleri.
- Kavramsal donanım, RF yaklaşımı ve her bileşen için A/B/C kurulum müdahalesi matrisi.

## Kaynaklar ve sınırlar

Verilen PDF/Excel dosyaları değiştirilmez. [Kaynak analizi](docs/source-analysis.md), Excel'de hangi verilerin bulunduğunu ve teknik adres/yerleşim dayanaklarını açıklar. Excel yalnız L1 sentetik akım içerir; diğer kanalların üretimi API/UI üzerinde etiketlidir. PD acquisition zinciri konsepttir; sentetik feature'lar kalibre gerçek PD ölçümü değildir. RF kapsama/pil ömrü, gerçek Modbus word order ve saha alarm eşikleri doğrulanmış değildir.

Teknik mimari [MASTER_SPEC.md](MASTER_SPEC.md) ve [architecture.md](docs/architecture.md); takım kuralları [AGENTS.md](AGENTS.md). Üretim/saha güvenlik sınırları [security.md](docs/security.md), kurulum kesintileri [installation-matrix.md](docs/installation-matrix.md), kablosuz seçimi [wireless-design.md](docs/wireless-design.md).

## Demo ve doğrulama

[Demo akışı](docs/demo-guide.md), [performans ölçümleri](docs/performance.md) ve [kabul matrisi](docs/acceptance.md) tekrar üretilebilir komutları ve gerçek sonuçları içerir. Son doğrulamada **62 Python testi, 7 tarayıcı testi ve 11 servis/kesinti kontrolü geçti**. 100/250/500 cihazın HTTP ve MQTT testlerinde **6.800/6.800 mesaj PostgreSQL'e kaydedildi**. Bu kısa sentetik testler gerçek saha doğruluğu veya koruma sertifikasyonu anlamına gelmez.

```powershell
docker compose exec api python -m pytest tests/unit tests/integration tests/modbus tests/source -q
python scripts/verify_stack.py --restarts
```

Frontend testleri `apps/web` içinde `npm run test:e2e`. Sırlar Git'e alınmaz. Runtime public cloud bağımlılığı yoktur; ilk paket/image indirmesi kurulum aşamasıdır. Tam çevrimdışı image aktarımı [deployment.md](docs/deployment.md) içinde.
