#pragma once
#include "core.hpp"

namespace gridsentinel {
// Port implementations own UART framing, stale-RX drain, DE turnaround and the complete
// bounded transaction deadline. send/receive are deliberately hidden behind read-only RTU.
class SerialTransaction {
 public:
    virtual ~SerialTransaction() = default;
    virtual std::size_t exchange(const std::array<std::uint8_t, 8>& read_request,
        std::uint8_t* response, std::size_t capacity, std::uint32_t deadline_ms) = 0;
};
class ReadOnlyRtu final : public ModbusReader {
 public:
    ReadOnlyRtu(SerialTransaction& mpr, SerialTransaction& tvoc) : ports_{&mpr, &tvoc} {}
    bool read(std::uint8_t port, std::uint8_t unit, ReadFunction function, ReadRange range,
        std::uint16_t* words, std::uint32_t timeout_ms) override {
        if (port > 1 || !words || timeout_ms < 10 || timeout_ms > 2000) return false;
        std::array<std::uint8_t, 8> request{};
        if (!make_read_request(unit, function, range, request)) return false;
        std::array<std::uint8_t, 255> response{};
        const auto size = ports_[port]->exchange(request, response.data(), response.size(), timeout_ms);
        return size <= response.size() && parse_read_response(response.data(), size, unit, function, range.count, words);
    }
 private:
    std::array<SerialTransaction*, 2> ports_;
};
// Commissioning may use this fail-closed port before physical drivers exist. It never
// fabricates data and never touches UART/BLE/Ethernet or a protection device.
class DisabledSerial final : public SerialTransaction {
 public:
    std::size_t exchange(const std::array<std::uint8_t, 8>&, std::uint8_t*, std::size_t, std::uint32_t) override { return 0; }
};
} // namespace gridsentinel
