# GridSentinel reference edge firmware

ESP32-S3 + external SPI Ethernet için **C++17 referans kaynak çekirdeği**. Fiziksel kart bağlı değildir. Salt okunur RTU çerçeveleri, kaynak haritası decoding, veri kalitesi, UTC, kalıcı sınırlandırılmış kuyruk, QoS1/PUBACK yeniden deneme, geri çekilme ve health/watchdog akışı host üzerinde gerçekten derlenip test edilir. ESP-IDF entry bilinçli olarak uncommissioned durumunda kalır; donanım ve ağ sürücülerini taklit ederek sağlıklı saha verisi üretmez.

| Dosya | İşlev |
|---|---|
| `include/gridsentinel/core.hpp`, `src/core.cpp` | Config/identity, boot self-test, UTC, quality, decoder, queue, reconnect, MQTT ve watchdog runtime |
| `include/gridsentinel/register_maps.hpp` | Python kaynak haritalarından üretilen MPR/TVOC metadata ve izinli okuma aralıkları |
| `include/gridsentinel/adapters.hpp` | İki-port read-only RTU adapter, bounded UART transaction seam, fail-closed disabled port |
| `include/gridsentinel/board.hpp` | Carrier ile eşlenen ESP32 GPIO atamaları; kendi başına pin/hardware etkinleştirmez |
| `test/host_tests.cpp` | 7 grupta gerçek C++ testleri; child process restart, disk journal ve hata enjeksiyonu |
| `test/file_journal.hpp` | POSIX host için fsync + atomic rename; gömülü NVS driver değildir |
| `main/main.cpp`, `CMakeLists.txt` | ESP-IDF project ve güvenli başlangıç; fiziksel portlar henüz uygulanmadı |
| `test/verification.json` | Çalıştırılan komut, compiler, image ID, tarih ve test edilen kaynak hash'leri |

Repo kökünden Windows PowerShell veya Linux:

```text
python edge/firmware/tools/generate_register_maps.py --check
python -m pytest tests/hardware -q
python edge/firmware/tools/run_host_tests.py
```

Son komut ayrı `gridsentinel-firmware-host-test:local` imajında g++ ile derler; uygulama container/image'larını değiştirmez. Derleyici build-time indirilir, runtime test `--network none` çalışır. Üretim uygulamasına dış runtime bağımlılığı eklenmez. Linux üzerinde mevcut compiler ile alternatif:

```sh
mkdir -p /tmp/gridsentinel-firmware-build
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -Iedge/firmware/include -Iedge/firmware/test edge/firmware/src/core.cpp edge/firmware/test/host_tests.cpp -o /tmp/gridsentinel-firmware-build/host-tests
/tmp/gridsentinel-firmware-build/host-tests
```

ESP-IDF kurulu bir geliştirme ortamında, **bu ortamda çalıştırılmamış** hedef derleme komutu:

```text
cd edge/firmware
idf.py set-target esp32s3
idf.py build
```

Windows'ta Espressif IDF PowerShell/Command Prompt, Linux'ta ESP-IDF `export.sh` ile etkinleştirilmiş shell kullanılır. 2026-09-11 envanterinde ESP-IDF, PlatformIO ve Arduino CLI yoktu. **Embedded build NOT_RUN; fiziksel UART/RS485/BLE/Ethernet/NVM/watchdog NOT_VALIDATED.** Host C++ PASS, firmware target compiled anlamına gelmez. Flash/cihaz yazma komutu bu teslimde çalıştırılmadı.

[Firmware işleyişi ve sınırlar](../../docs/hardware/firmware.md) · [Carrier pin/net tasarımı](../../hardware/pcb/README.md).
