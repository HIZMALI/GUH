#include "gridsentinel/core.hpp"
#include "gridsentinel/adapters.hpp"
#include "gridsentinel/board.hpp"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// Deliberate uncommissioned ESP-IDF entry. Physical adapters are NOT implemented here.
// Do not replace durable storage with RAM and call the result store-and-forward.
extern "C" void app_main() {
    constexpr std::uint8_t vector[]{1, 3, 0, 0, 0, 2};
    const bool self_test = gridsentinel::modbus_crc16(vector, sizeof vector) == 0x0BC4;
    ESP_LOGI("GridSentinel", "Reference core self-test: %s", self_test ? "pass" : "fail");
    ESP_LOGW("GridSentinel", "UNCOMMISSIONED: NVS journal, UART, radio, UTC, TLS MQTT and watchdog ports required; hardware reads and networking disabled");
    // Cooperative idle; no UART traffic, GPIO field control, radio or external network operation.
    for (;;) vTaskDelay(pdMS_TO_TICKS(1000));
}
