# Kurulum

## Gereksinimler
Docker Desktop/Engine ve Compose v2; bootstrap için Python3.10+. İlk image/package indirmesi için internet; çalışma sırasında public cloud bağımlılığı yoktur. Windows'ta Docker Linux containers/WSL2 motorunu başlatın. 3000,8000,1883,1502 loopback portları boş olmalı. Donanım, broker sağlayıcısı, gerçek SCADA veya SMS hesabı gerekmez.

Repo kökünde:

```powershell
python scripts/run_demo.py --scenario combined_thermal_pd
```

Bu komut `.env` yoksa rastgele sırları oluşturur, Docker servislerini build/başlatır, health bekler ve senaryoyu seçer. Var olan `.env` üzerine yazmaz. Sonrasında [yerel ekranı](http://localhost:3000) açın. Kullanıcı `ADMIN_USERNAME`, parola `.env` içindeki `ADMIN_PASSWORD`; salt okuma için `viewer`/`VIEWER_PASSWORD`, operatör için `operator`/`OPERATOR_PASSWORD`.

Eşdeğer ayrı adımlar:

```powershell
python scripts/bootstrap.py
docker compose up -d --build
docker compose ps
python scripts/run_demo.py --connect-only --scenario combined_thermal_pd
```

Kurulumdan sonra `docker compose up -d` yeterli. `.env` özel dosyadır; paylaşmayın. `.env.example` yalnız anahtar şablonudur, çalışır parola içermez.

## Sorun giderme
`docker compose logs --tail=100 api simulator mqtt scada web` uygulama loglarını gösterir. Docker daemon hatasında Docker Desktop motorunu başlatın. API health `http://localhost:8000/health`; endpoint sözleşmesi `docs/api-contract.md` içindedir. Telemetry'nin görünmesi simulator'ın ilk döngüsü ve cihaz sayısına göre birkaç saniye sürebilir. DB/bridge kopukluğu arayüzde açık gösterilir.

`.env` parolalarını kalıcı DB oluşturulduktan sonra rastgele değiştirmek PostgreSQL hesabını otomatik değiştirmez. Sır rotasyonu kontrollü yapılmalıdır. Volümleri silerek düzeltme varsayılan çözüm değildir.

## Durdurma ve saklama
`docker compose stop` servisleri durdurur ve veriyi korur. `docker compose down` ağ/container'ları kaldırır, adlandırılmış volume'ları korur. `down -v` veriyi siler; normal kullanım için gerekli değildir.

## Geliştirme ve test
Backend bağımlılıkları `requirements.txt`, frontend kilidi `apps/web/package-lock.json`. Compose içinde `docker compose exec api python -m pytest tests/unit tests/integration tests/modbus -q`; tarayıcı E2E için `apps/web` test script'lerini kullanın. Backend izole testlerde SQLite, demo stack'te PostgreSQL kullanır. Yük/restart doğrulama komutları `performance.md` ve `demo-guide.md` içindedir.

Kaynak veri çıkarımını yeniden yapmak için Python ortamına pypdf ve openpyxl kurup `python scripts/analyze_sources.py` ve `python scripts/import_dataset.py` çalıştırılabilir. Normal demo, kontrol edilmiş JSON veriyle çalışır; workbook paketlerine runtime bağımlılığı yoktur.
