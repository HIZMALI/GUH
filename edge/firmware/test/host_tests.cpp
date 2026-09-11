#include "gridsentinel/core.hpp"
#include "gridsentinel/adapters.hpp"
#include "gridsentinel/register_maps.hpp"
#include "gridsentinel/board.hpp"
#include "file_journal.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/wait.h>
#include <unistd.h>
using namespace gridsentinel;
static int checks = 0;
#define CHECK(expression) do { ++checks; if (!(expression)) throw std::runtime_error(std::string(__func__) + ":" + std::to_string(__LINE__) + " " #expression); } while(false)
struct MemoryJournal final : Journal {
    std::vector<std::uint8_t> data;
    bool fail = false;
    std::size_t load(std::uint8_t* out, std::size_t cap) override {
        if (data.size() <= cap) std::copy(data.begin(), data.end(), out);
        return data.size();
    }
    bool commit(const std::uint8_t* input, std::size_t size) override {
        if (fail) return false;
        data.assign(input, input + size); return true;
    }
};
Frame frame(std::uint64_t sequence, const char* device = "EDGE-001") {
    Frame result{}; result.sequence = sequence; result.utc_ms = 1789056000000LL + static_cast<std::int64_t>(sequence);
    std::snprintf(result.message_id.data(), result.message_id.size(), "%s-%llu", device, static_cast<unsigned long long>(sequence));
    std::snprintf(result.payload.data(), result.payload.size(), "{\"message_id\":\"%s\",\"source\":\"generated_synthetic\"}", result.message_id.data());
    return result;
}
const RegisterSpec& spec(const char* name) {
    for (const auto& item : kMprRegisters) if (!std::strcmp(item.name, name)) return item;
    throw std::runtime_error(std::string("missing map: ") + name);
}
void protocol_test() {
    std::array<std::uint8_t, 8> request{};
    CHECK(make_read_request(1, ReadFunction::Holding, {0, 2}, request));
    CHECK((request == std::array<std::uint8_t, 8>{1, 3, 0, 0, 0, 2, 0xC4, 0x0B}));
    for (auto fc : {0, 1, 2, 5, 6, 15, 16, 22, 23, 0x80}) CHECK(!make_read_request(1, static_cast<ReadFunction>(fc), {1000, 1}, request));
    CHECK(!make_read_request(0, ReadFunction::Holding, {0, 1}, request));
    CHECK(!make_read_request(248, ReadFunction::Input, {0, 1}, request));
    CHECK(!make_read_request(1, ReadFunction::Holding, {0, 126}, request));
    CHECK(!make_read_request(1, ReadFunction::Holding, {65535, 2}, request));
    CHECK(!make_read_request(1, ReadFunction::Holding, {0, 0}, request));
    std::array<std::uint8_t, 9> response{1, 3, 4, 0x12, 0x34, 0xAB, 0xCD, 0, 0};
    const auto crc = modbus_crc16(response.data(), 7); response[7] = crc & 255; response[8] = crc >> 8;
    std::uint16_t words[2]{};
    CHECK(parse_read_response(response.data(), 9, 1, ReadFunction::Holding, 2, words));
    CHECK(words[0] == 0x1234 && words[1] == 0xABCD);
    CHECK(!parse_read_response(response.data(), 8, 1, ReadFunction::Holding, 2, words));
    CHECK(!parse_read_response(response.data(), 9, 2, ReadFunction::Holding, 2, words));
    CHECK(!parse_read_response(response.data(), 9, 1, ReadFunction::Input, 2, words));
    response[3] ^= 1;
    CHECK(!parse_read_response(response.data(), 9, 1, ReadFunction::Holding, 2, words));
    const std::uint8_t exception[]{1, 0x83, 2, 0xC0, 0xF1};
    CHECK(!parse_read_response(exception, sizeof exception, 1, ReadFunction::Holding, 2, words));
}
void decoding_test() {
    const std::uint16_t positive[]{0, 2300}, negative[]{0xFFFF, 0xF830}, swapped[]{2300, 0};
    CHECK(std::abs(decode_register(positive, 2, spec("voltage_l1"), WordOrder::Big).value - 230) < 0.0001);
    CHECK(std::abs(decode_register(swapped, 2, spec("voltage_l1"), WordOrder::Little).value - 230) < 0.0001);
    CHECK(std::abs(decode_register(negative, 2, spec("active_power_l1"), WordOrder::Big).value + 200) < 0.0001);
    CHECK(decode_register(positive, 1, spec("voltage_l1"), WordOrder::Big).quality == Quality::Missing);
    const std::uint16_t counter[]{0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF}; std::uint64_t raw = 0;
    CHECK(decode_raw_u64(counter, 4, 4, WordOrder::Big, raw));
    CHECK(raw == std::numeric_limits<std::uint64_t>::max());
    CHECK(!decode_raw_u64(counter, 4, 4, static_cast<WordOrder>(99), raw));
    RegisterSpec wide{"counter", 0, 4, 1, false, 1};
    CHECK(decode_register(counter, 4, wide, WordOrder::Big).quality == Quality::Invalid); // no lossy double counter
    const std::uint16_t single[]{0x8101}; RegisterSpec flags{"flags", 84, 1, 1, false, 1};
    CHECK(decode_register(single, 1, flags, WordOrder::Big).value == 0x8101);
    CHECK(decode_firmware(0x0300, 0).major == 3);
    CHECK(decode_firmware(0x0201, 9).patch == 9);
    CHECK(!decode_firmware(0xFFFF, 0xFFFF).valid);
    const auto trip = decode_trip({0x8401, 0xC020, 0xFFFF & 7, 17078, 0x0922, 12}, 0);
    CHECK(trip.present && trip.quality == Quality::Good);
    CHECK(trip.detector_low == 0x401 && trip.detector_high == 0x4020 && trip.relays == 7);
    CHECK(trip.utc_seconds == 1475573652); // ABB example: 2016-10-04 09:34:12, explicit UTC assumption.
    CHECK(decode_trip({1, 0, 1, 17078, 0x0922, 12}, 10800).utc_seconds == trip.utc_seconds - 10800);
    CHECK(decode_trip({0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF, 0xFFFF}, 0).quality == Quality::Missing);
    CHECK(decode_trip({0xFFFF, 0, 0, 17078, 0x0922, 12}, 0).quality == Quality::Invalid);
    CHECK(decode_trip({1, 0, 0, 17078, 0x183B, 12}, 0).quality == Quality::Invalid);
    CHECK(decode_trip({1, 0, 0, 17078, 0x003C, 12}, 0).quality == Quality::Invalid);
    CHECK(decode_trip({1, 0, 0, 17078, 0, 60}, 0).quality == Quality::Invalid);
}
void time_and_backoff_test() {
    UtcClock clock; std::int64_t utc = 0;
    CHECK(!clock.now(0, utc)); CHECK(!clock.synchronize(0, 0));
    CHECK(clock.synchronize(1789056000000LL, 100)); CHECK(clock.now(1100, utc));
    CHECK(utc == 1789056001000LL); CHECK(!clock.now(99, utc));
    CHECK(!clock.synchronize(1789056000001LL, 1100)); CHECK(!clock.now(1100, utc));
    CHECK(clock.synchronize(1789056002000LL, 1200));
    CHECK(!clock.now(1200 + UtcClock::kMaxHoldoverMs + 1, utc));
    CHECK(!clock.synchronize(1789056002001LL, 1200 + UtcClock::kMaxHoldoverMs + 1));
    CHECK(!clock.synchronize(1789056002002LL, 1200 + UtcClock::kMaxHoldoverMs + 2));
    Backoff first(123), second(123), other(456);
    std::uint64_t now = 0; bool distinct = false;
    for (int i = 0; i < 40; ++i) {
        const auto due = first.fail(now); const auto same = second.fail(now); const auto different = other.fail(now);
        CHECK(due == same && due > now && due - now <= 30000);
        CHECK(!first.due(due - 1) && first.due(due)); distinct = distinct || due != different; now = due;
    }
    CHECK(distinct); CHECK(first.attempts() == 32); first.success(); CHECK(first.attempts() == 0 && first.due(0));
}
void queue_test() {
    MemoryJournal journal; PersistentQueue queue(journal);
    CHECK(!queue.begin("bad/id")); CHECK(queue.begin("EDGE-001")); CHECK(queue.healthy());
    CHECK(!queue.enqueue(frame(2))); CHECK(!queue.enqueue(frame(1, "EDGE-002")));
    for (std::size_t i = 1; i <= kQueueCapacity; ++i) CHECK(queue.enqueue(frame(i)));
    CHECK(queue.size() == 8 && queue.next_sequence() == 9);
    CHECK(!queue.enqueue(frame(9))); CHECK(queue.dropped() == 1 && queue.front()->sequence == 1);
    CHECK(!queue.acknowledge(2)); CHECK(queue.acknowledge(1));
    PersistentQueue reboot(journal); CHECK(reboot.begin("EDGE-001")); CHECK(reboot.front()->sequence == 2);
    CHECK(reboot.dropped() == 1 && reboot.next_sequence() == 9); CHECK(reboot.enqueue(frame(9)));
    journal.fail = true; CHECK(!reboot.acknowledge(2)); CHECK(!reboot.healthy()); CHECK(reboot.front()->sequence == 2);
    CHECK(!reboot.enqueue(frame(10))); journal.fail = false;
    PersistentQueue uncertain_reboot(journal); CHECK(uncertain_reboot.begin("EDGE-001")); CHECK(uncertain_reboot.front()->sequence == 2);
    CHECK(!uncertain_reboot.begin("DIFFERENT")); CHECK(!uncertain_reboot.healthy());
    journal.data[20] ^= 1; PersistentQueue corrupt(journal); CHECK(!corrupt.begin("EDGE-001")); CHECK(!corrupt.healthy());
    journal.data.resize(4); CHECK(!corrupt.begin("EDGE-001"));
}
struct TestSerial final : SerialTransaction {
    unsigned calls = 0; bool timeout = false; std::uint32_t deadline = 0;
    std::size_t exchange(const std::array<std::uint8_t, 8>& request, std::uint8_t* out, std::size_t cap, std::uint32_t bound) override {
        ++calls; deadline = bound; CHECK(request[1] == 3 || request[1] == 4); CHECK(cap >= 7);
        if (timeout) return 0;
        out[0] = request[0]; out[1] = request[1]; out[2] = 2; out[3] = 0xAB; out[4] = 0xCD;
        const auto crc = modbus_crc16(out, 5); out[5] = crc & 255; out[6] = crc >> 8; return 7;
    }
};
void adapter_test() {
    CHECK(board::kMpr.tx == 17 && board::kMpr.rx == 18 && board::kMpr.de_re == 15);
    CHECK(board::kTvoc.tx == 4 && board::kTvoc.rx == 5 && board::kTvoc.de_re == 6);
    TestSerial mpr, tvoc; ReadOnlyRtu adapter(mpr, tvoc); std::uint16_t word = 0;
    CHECK(adapter.read(1, 2, ReadFunction::Input, {1300, 1}, &word, 250));
    CHECK(word == 0xABCD && mpr.calls == 0 && tvoc.calls == 1 && tvoc.deadline == 250);
    CHECK(!adapter.read(2, 2, ReadFunction::Input, {1300, 1}, &word, 250));
    CHECK(!adapter.read(1, 2, static_cast<ReadFunction>(6), {1000, 1}, &word, 250)); CHECK(tvoc.calls == 1);
    tvoc.timeout = true; CHECK(!adapter.read(1, 2, ReadFunction::Input, {1300, 1}, &word, 250));
    CHECK(!adapter.read(1, 2, ReadFunction::Input, {1300, 1}, &word, 2001));
}
struct FakeModbus final : ModbusReader {
    bool online = true; std::uint8_t major = 2; std::vector<ReadRange> reads;
    Source source() const override { return Source::GeneratedSynthetic; }
    bool read(std::uint8_t port, std::uint8_t unit, ReadFunction fc, ReadRange range, std::uint16_t* out, std::uint32_t timeout) override {
        CHECK(fc == ReadFunction::Holding && timeout == 250 && unit == (port ? 2 : 1));
        CHECK(range.address != 213 && range.address != 1000 && range.address != 1100);
        reads.push_back(range); if (!online) return false;
        std::fill(out, out + range.count, 0);
        if (!port) { out[7] = 10000; out[59] = 5000; out[79] = 33; out[73] = 17; }
        else if (range.address == 800) out[0] = static_cast<std::uint16_t>(major << 8);
        else if (range.address == 100) std::fill(out, out + range.count, 0xFFFF);
        return true;
    }
    bool sensor_read() const { for (const auto& item : reads) if (item.address == 222) return true; return false; }
};
struct FakeWireless final : WirelessReceiver {
    WirelessObservation observation{{28, Quality::Good}, {55, Quality::Good}, 0, true, "TH-A / H1"};
    WirelessObservation latest() override { return observation; }
};
struct FakeMqtt final : MqttPublisher {
    bool online = false; PublishResult result = PublishResult::Disconnected; unsigned attempts = 0, publishes = 0;
    std::vector<std::string> ids, payloads;
    bool connect(const Config& config) override { CHECK(config.credentials_provisioned && config.approved_local_endpoint); ++attempts; return online; }
    PublishResult publish(const char* topic, const Frame& f, std::uint8_t qos) override {
        CHECK(std::string(topic) == "gridsentinel/telemetry/EDGE-001" && qos == 1);
        ++publishes; ids.emplace_back(f.message_id.data()); payloads.emplace_back(f.payload.data()); return result;
    }
};
struct FakeWatchdog final : Watchdog { unsigned feeds = 0; void feed() override { ++feeds; } };
Config configuration() { Config config; config.device_id = "EDGE-001"; config.panel_id = "PNL-001"; return config; }
void runtime_test() {
    MemoryJournal journal; PersistentQueue queue(journal); UtcClock clock; FakeModbus modbus; FakeWireless wireless; FakeMqtt mqtt; FakeWatchdog watchdog;
    Config config = configuration(); config.mqtt_enabled = true; config.broker_host = "broker.local";
    Config invalid_order = configuration(); invalid_order.mpr_word_order = static_cast<WordOrder>(99); CHECK(!valid_config(invalid_order));
    CHECK(!valid_config(config)); config.credentials_provisioned = config.approved_local_endpoint = true; CHECK(valid_config(config));
    Runtime runtime(config, queue, clock, modbus, wireless, mqtt, watchdog); CHECK(runtime.boot());
    runtime.tick(0); CHECK(queue.size() == 0 && !runtime.health().time_valid && watchdog.feeds == 1);
    CHECK(clock.synchronize(1789056000000LL, 0)); runtime.tick(2000);
    CHECK(queue.size() == 1 && mqtt.attempts == 1 && !modbus.sensor_read());
    CHECK(std::string(queue.front()->payload.data()).find("\"sensor_status_x2_raw\":null") != std::string::npos);
    CHECK(std::string(queue.front()->payload.data()).find("\"latest_trip_quality\":\"missing\"") != std::string::npos);
    runtime.tick(2001); CHECK(mqtt.attempts == 1); // Failed connect cannot spin.
    mqtt.online = true; mqtt.result = PublishResult::Failed; runtime.tick(4000);
    CHECK(queue.size() == 2 && mqtt.publishes == 1); const auto replay_id = mqtt.ids.front();
    mqtt.result = PublishResult::Acknowledged; runtime.tick(8000);
    CHECK(mqtt.ids.back() == replay_id && queue.front()->sequence == 2); // same durable ID after ambiguous delivery
    CHECK(runtime.health().mpr_online && runtime.health().tvoc_online && runtime.health().storage_ok);
    CHECK(runtime.health().publish_retries == 2 && watchdog.feeds == 5);
    modbus.reads.clear(); modbus.major = 3; runtime.tick(10000); CHECK(modbus.sensor_read());
    CHECK(mqtt.payloads.back().find("\"current_l1\":10") != std::string::npos);
    // Separate no-publish sample checks bad identity and stale/missing serialization.
    MemoryJournal second_journal; PersistentQueue second_queue(second_journal); Config offline_config = configuration();
    Runtime offline(offline_config, second_queue, clock, modbus, wireless, mqtt, watchdog); CHECK(offline.boot());
    modbus.online = false; wireless.observation.observed_monotonic_ms = 0; offline.tick(20000);
    const std::string payload = second_queue.front()->payload.data();
    CHECK(payload.find("\"current_l1\":null") != std::string::npos);
    CHECK(payload.find("\"humidity_pct\":\"stale\"") != std::string::npos);
    CHECK(payload.find("\"installed_modules\":null") != std::string::npos);
    CHECK(payload.find("\"event\":null") != std::string::npos);
    CHECK(!offline.health().mpr_online && !offline.health().tvoc_online);
    wireless.observation.point = "wrong-point"; offline.tick(22000); CHECK(second_queue.size() == 2);
    CHECK(second_queue.acknowledge(1)); CHECK(std::string(second_queue.front()->payload.data()).find("\"humidity_pct\":\"invalid\"") != std::string::npos);
    // Physical RTU cannot be mislabeled generated synthetic, even if a caller supplies it by mistake.
    MemoryJournal physical_journal; PersistentQueue physical_queue(physical_journal); TestSerial serial1, serial2;
    ReadOnlyRtu physical(serial1, serial2);
    Runtime mislabeled(offline_config, physical_queue, clock, physical, wireless, mqtt, watchdog);
    CHECK(!mislabeled.boot()); mislabeled.tick(24000); CHECK(serial1.calls == 0 && serial2.calls == 0);
    offline_config.source = Source::DeviceReadUnverified;
    Runtime uncommissioned(offline_config, physical_queue, clock, physical, wireless, mqtt, watchdog);
    CHECK(uncommissioned.boot()); uncommissioned.tick(24000);
    CHECK(serial1.calls == 0 && serial2.calls == 0 && !uncommissioned.health().mpr_online);
}
void file_restart_test(const char* executable) {
    char pattern[] = "/tmp/gridsentinel-firmware-XXXXXX"; const char* directory = ::mkdtemp(pattern); CHECK(directory != nullptr);
    const auto path = std::string(directory) + "/queue.bin";
    {
        FileJournal journal(path); PersistentQueue queue(journal); CHECK(queue.begin("EDGE-001")); CHECK(queue.enqueue(frame(1))); CHECK(queue.enqueue(frame(2)));
    }
    const auto child = ::fork(); CHECK(child >= 0);
    if (child == 0) { ::execl(executable, executable, "--resume", path.c_str(), nullptr); ::_exit(127); }
    int status = 0; CHECK(::waitpid(child, &status, 0) == child); CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0);
    FileJournal journal(path); PersistentQueue queue(journal); CHECK(queue.begin("EDGE-001"));
    CHECK(queue.front()->sequence == 2 && queue.next_sequence() == 4 && queue.size() == 2);
    // An interrupted temp write leaves the complete committed snapshot recoverable.
    { const auto pending = path + ".pending"; FILE* file = std::fopen(pending.c_str(), "wb"); CHECK(file != nullptr); CHECK(std::fwrite("bad", 1, 3, file) == 3); std::fclose(file); }
    PersistentQueue interrupted(journal); CHECK(interrupted.begin("EDGE-001")); CHECK(interrupted.next_sequence() == 4);
    // This directory was created by this test; no user path is recursively removed.
    std::filesystem::remove_all(directory);
}
int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--resume") {
            FileJournal journal(argv[2]); PersistentQueue queue(journal); CHECK(queue.begin("EDGE-001"));
            CHECK(queue.front()->sequence == 1 && queue.next_sequence() == 3); CHECK(queue.acknowledge(1)); CHECK(queue.enqueue(frame(3))); return 0;
        }
        protocol_test(); decoding_test(); time_and_backoff_test(); queue_test(); adapter_test(); runtime_test(); file_restart_test(argv[0]);
        std::cout << "{\"status\":\"PASS\",\"groups\":7,\"assertions\":" << checks << ",\"target\":\"Linux host C++17\",\"embedded_build\":\"NOT_RUN\"}\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << "FAIL " << error.what() << '\n'; return 1; }
}
