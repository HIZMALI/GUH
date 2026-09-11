#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace gridsentinel {
constexpr std::size_t kQueueCapacity = 8;
constexpr std::size_t kPayloadCapacity = 3072;
constexpr std::size_t kSnapshotCapacity = 27000;
enum class Quality : std::uint8_t { Good, Missing, Invalid, Stale };
enum class Source : std::uint8_t { GeneratedSynthetic, DeviceReadUnverified };
enum class WordOrder : std::uint8_t { Big, Little };
enum class ReadFunction : std::uint8_t { Holding = 3, Input = 4 };
enum class PublishResult { Acknowledged, Disconnected, Failed };
struct RegisterSpec { const char* name; std::uint16_t address; std::uint8_t width; double scale; bool is_signed; std::uint8_t source_page; };
struct ReadRange { std::uint16_t address; std::uint16_t count; };
struct Value { double value = 0; Quality quality = Quality::Missing; };
struct FirmwareVersion { std::uint8_t major = 0, minor = 0, patch = 0; bool valid = false; };
struct Trip { bool present = false; Quality quality = Quality::Missing; std::uint16_t detector_low = 0, detector_high = 0, relays = 0; std::int64_t utc_seconds = 0; };
struct Config {
    const char* device_id = "";
    const char* panel_id = "";
    const char* broker_host = "";
    std::uint16_t broker_port = 8883;
    std::uint8_t mpr_unit = 1, tvoc_unit = 2;
    std::uint32_t poll_interval_ms = 2000, timeout_ms = 250, wireless_stale_ms = 15000;
    WordOrder mpr_word_order = WordOrder::Big; // Unverified until device commissioning.
    std::int32_t tvoc_utc_offset_seconds = 0; // Unverified device timezone; never infer from host timezone.
    bool credentials_provisioned = false, approved_local_endpoint = false;
    bool hardware_reads_enabled = false, mqtt_enabled = false;
    Source source = Source::GeneratedSynthetic;
};
bool valid_config(const Config& config);
const char* quality_name(Quality quality);
std::uint16_t modbus_crc16(const std::uint8_t* bytes, std::size_t length);
bool make_read_request(std::uint8_t unit, ReadFunction function, ReadRange range, std::array<std::uint8_t, 8>& request);
bool parse_read_response(const std::uint8_t* bytes, std::size_t length, std::uint8_t unit,
                         ReadFunction function, std::uint16_t count, std::uint16_t* words);
Value decode_register(const std::uint16_t* words, std::size_t count, const RegisterSpec& spec, WordOrder order);
bool decode_raw_u64(const std::uint16_t* words, std::size_t count, std::uint8_t width, WordOrder order, std::uint64_t& raw);
FirmwareVersion decode_firmware(std::uint16_t xxyy, std::uint16_t zz);
Trip decode_trip(const std::array<std::uint16_t, 6>& words, std::int32_t utc_offset_seconds);

class UtcClock {
 public:
    bool synchronize(std::int64_t utc_ms, std::uint64_t monotonic_ms);
    bool now(std::uint64_t monotonic_ms, std::int64_t& utc_ms) const;
    void invalidate() { valid_ = false; }
    static constexpr std::uint64_t kMaxHoldoverMs = 15 * 60 * 1000;
 private:
    std::int64_t utc_ms_ = 0;
    std::uint64_t monotonic_ms_ = 0;
    bool valid_ = false, anchored_ = false;
};
class Backoff {
 public:
    explicit Backoff(std::uint32_t seed = 1) : state_(seed ? seed : 1) {}
    std::uint64_t fail(std::uint64_t now_ms);
    bool due(std::uint64_t now_ms) const { return now_ms >= due_ms_; }
    void success() { attempts_ = 0; due_ms_ = 0; }
    std::uint32_t attempts() const { return attempts_; }
 private:
    std::uint32_t state_ = 1, attempts_ = 0;
    std::uint64_t due_ms_ = 0;
};
struct Frame {
    std::uint64_t sequence = 0;
    std::int64_t utc_ms = 0;
    std::array<char, 96> message_id{};
    std::array<char, kPayloadCapacity> payload{};
};
// Success means an atomic durable snapshot. On any uncertain failure the queue fails closed;
// a reboot must reload the last complete snapshot before it can publish or allocate another ID.
// NVS/FRAM port is an explicit hardware seam. FileJournal implements this contract for host tests.
class Journal {
 public:
    virtual ~Journal() = default;
    virtual std::size_t load(std::uint8_t* destination, std::size_t capacity) = 0;
    virtual bool commit(const std::uint8_t* data, std::size_t length) = 0;
};
class PersistentQueue {
 public:
    explicit PersistentQueue(Journal& journal) : journal_(journal) {}
    bool begin(const char* device_id);
    bool enqueue(const Frame& frame);
    bool acknowledge(std::uint64_t sequence);
    const Frame* front() const { return state_.count ? &state_.frames[0] : nullptr; }
    std::size_t size() const { return state_.count; }
    std::uint64_t next_sequence() const { return state_.next_sequence; }
    std::uint64_t dropped() const { return state_.dropped; }
    bool healthy() const { return healthy_; }
 private:
    struct State { std::array<char, 32> owner{}; std::uint64_t next_sequence = 1, dropped = 0; std::uint16_t count = 0; std::array<Frame, kQueueCapacity> frames{}; };
    bool save_candidate();
    bool restore(std::size_t length);
    Journal& journal_;
    State state_{}, candidate_{};
    std::array<std::uint8_t, kSnapshotCapacity> buffer_{};
    bool healthy_ = false;
};
class ModbusReader {
 public:
    virtual ~ModbusReader() = default;
    virtual Source source() const { return Source::DeviceReadUnverified; }
    virtual bool read(std::uint8_t port, std::uint8_t unit, ReadFunction function, ReadRange range,
                      std::uint16_t* words, std::uint32_t timeout_ms) = 0;
};
struct WirelessObservation {
    Value temperature, humidity;
    std::uint64_t observed_monotonic_ms = 0;
    bool identity_validated = false;
    const char* point = "TH-A / H1";
};
class WirelessReceiver {
 public:
    virtual ~WirelessReceiver() = default;
    virtual WirelessObservation latest() = 0;
};
class MqttPublisher {
 public:
    virtual ~MqttPublisher() = default;
    virtual bool connect(const Config& config) = 0;
    // Acknowledged means broker QoS1 PUBACK, not application/database commit.
    virtual PublishResult publish(const char* topic, const Frame& frame, std::uint8_t qos) = 0;
};
class Watchdog {
 public:
    virtual ~Watchdog() = default;
    virtual void feed() = 0; // MCU health only; no signal leaves the carrier toward protection equipment.
};
struct Health { bool boot_ok = false, time_valid = false, mpr_online = false, tvoc_online = false, mqtt_online = false, storage_ok = false; std::uint64_t cycles = 0, queue_drops = 0, publish_retries = 0; };
class Runtime {
 public:
    Runtime(Config config, PersistentQueue& queue, UtcClock& clock, ModbusReader& modbus,
            WirelessReceiver& wireless, MqttPublisher& mqtt, Watchdog& watchdog);
    bool boot();
    void tick(std::uint64_t monotonic_ms);
    const Health& health() const { return health_; }
 private:
    void sample(std::uint64_t monotonic_ms, std::int64_t utc_ms);
    Config config_;
    PersistentQueue& queue_;
    UtcClock& clock_;
    ModbusReader& modbus_;
    WirelessReceiver& wireless_;
    MqttPublisher& mqtt_;
    Watchdog& watchdog_;
    Backoff backoff_;
    Health health_{};
    std::uint64_t next_poll_ms_ = 0;
    bool connected_ = false;
};
} // namespace gridsentinel
