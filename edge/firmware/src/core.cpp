#include "gridsentinel/core.hpp"
#include "gridsentinel/register_maps.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <limits>

namespace gridsentinel {
namespace {
bool identifier(const char* text) {
    if (!text) return false;
    const auto size = std::strlen(text);
    if (size == 0 || size > 31) return false;
    for (std::size_t i = 0; i < size; ++i) {
        const char c = text[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_')) return false;
    }
    return true;
}
std::uint32_t identity_seed(const char* value) {
    std::uint32_t hash = 2166136261u;
    if (value) for (const char* p = value; *p; ++p) hash = (hash ^ static_cast<std::uint8_t>(*p)) * 16777619u;
    return hash;
}
bool format_id(char* destination, std::size_t size, const char* device, std::uint64_t sequence) {
    const int written = std::snprintf(destination, size, "%s-%llu", device, static_cast<unsigned long long>(sequence));
    return written > 0 && static_cast<std::size_t>(written) < size;
}
bool iso_time(std::int64_t utc_ms, char* destination, std::size_t size) {
    if (utc_ms < 0) return false;
    const std::time_t seconds = static_cast<std::time_t>(utc_ms / 1000);
    const std::tm* utc = std::gmtime(&seconds); // Single-thread core; no global host timezone is used.
    return utc && std::strftime(destination, size, "%Y-%m-%dT%H:%M:%SZ", utc) != 0;
}
void numeric(Value value, char* destination, std::size_t size) {
    if (value.quality != Quality::Good || !std::isfinite(value.value)) std::snprintf(destination, size, "null");
    else std::snprintf(destination, size, "%.6g", value.value);
}
const RegisterSpec* mpr_spec(const char* name) {
    for (const auto& spec : kMprRegisters) if (std::strcmp(spec.name, name) == 0) return &spec;
    return nullptr;
}
Value mpr_value(const std::array<std::uint16_t, 86>& words, bool online, const char* name, WordOrder order) {
    const RegisterSpec* spec = mpr_spec(name);
    if (!online || !spec || spec->address + spec->width > words.size()) return {};
    return decode_register(words.data() + spec->address, spec->width, *spec, order);
}
} // namespace

bool valid_config(const Config& c) {
    return (c.source == Source::GeneratedSynthetic || c.source == Source::DeviceReadUnverified) &&
        (c.mpr_word_order == WordOrder::Big || c.mpr_word_order == WordOrder::Little) &&
        identifier(c.device_id) && identifier(c.panel_id) && c.mpr_unit >= 1 && c.mpr_unit <= 247 &&
        c.tvoc_unit >= 1 && c.tvoc_unit <= 247 && c.poll_interval_ms >= 100 && c.poll_interval_ms <= 3600000 &&
        c.timeout_ms >= 10 && c.timeout_ms <= 2000 && c.wireless_stale_ms >= c.poll_interval_ms &&
        std::abs(static_cast<std::int64_t>(c.tvoc_utc_offset_seconds)) <= 14 * 3600 &&
        (!c.mqtt_enabled || (c.broker_host && c.broker_host[0] && c.broker_port > 0 &&
                             c.credentials_provisioned && c.approved_local_endpoint));
}
const char* quality_name(Quality q) {
    switch (q) { case Quality::Good: return "good"; case Quality::Missing: return "missing";
                 case Quality::Invalid: return "invalid"; case Quality::Stale: return "stale"; }
    return "invalid";
}
std::uint16_t modbus_crc16(const std::uint8_t* bytes, std::size_t length) {
    std::uint16_t crc = 0xFFFF;
    for (std::size_t i = 0; i < length; ++i) {
        crc ^= bytes[i];
        for (int bit = 0; bit < 8; ++bit) crc = static_cast<std::uint16_t>((crc >> 1) ^ ((crc & 1) ? 0xA001 : 0));
    }
    return crc;
}
bool make_read_request(std::uint8_t unit, ReadFunction function, ReadRange range, std::array<std::uint8_t, 8>& output) {
    const auto fc = static_cast<std::uint8_t>(function);
    if (unit == 0 || unit > 247 || (fc != 3 && fc != 4) || range.count == 0 || range.count > 125 ||
        static_cast<std::uint32_t>(range.address) + range.count > 65536) return false;
    output = {unit, fc, static_cast<std::uint8_t>(range.address >> 8), static_cast<std::uint8_t>(range.address),
              static_cast<std::uint8_t>(range.count >> 8), static_cast<std::uint8_t>(range.count), 0, 0};
    const auto crc = modbus_crc16(output.data(), 6);
    output[6] = static_cast<std::uint8_t>(crc);
    output[7] = static_cast<std::uint8_t>(crc >> 8);
    return true;
}
bool parse_read_response(const std::uint8_t* bytes, std::size_t length, std::uint8_t unit,
                         ReadFunction function, std::uint16_t count, std::uint16_t* words) {
    const auto fc = static_cast<std::uint8_t>(function);
    if (!bytes || !words || count == 0 || count > 125 || unit == 0 || unit > 247 ||
        (fc != 3 && fc != 4) || length != 5u + 2u * count || bytes[0] != unit ||
        bytes[1] != fc || bytes[2] != count * 2) return false;
    const auto crc = modbus_crc16(bytes, length - 2);
    if (bytes[length - 2] != (crc & 255) || bytes[length - 1] != (crc >> 8)) return false;
    for (std::size_t i = 0; i < count; ++i) words[i] = static_cast<std::uint16_t>((bytes[3 + i * 2] << 8) | bytes[4 + i * 2]);
    return true;
}
bool decode_raw_u64(const std::uint16_t* words, std::size_t count, std::uint8_t width, WordOrder order, std::uint64_t& raw) {
    if (!words || !width || width > 4 || count < width || (order != WordOrder::Big && order != WordOrder::Little)) return false;
    raw = 0;
    for (std::size_t i = 0; i < width; ++i) raw = (raw << 16) | words[order == WordOrder::Big ? i : width - 1 - i];
    return true;
}
Value decode_register(const std::uint16_t* words, std::size_t count, const RegisterSpec& spec, WordOrder order) {
    if (!words || count < spec.width) return {};
    if (spec.width == 0 || spec.width > 4 || !std::isfinite(spec.scale)) return {0, Quality::Invalid};
    std::uint64_t raw = 0;
    if (!decode_raw_u64(words, count, spec.width, order, raw)) return {0, Quality::Invalid};
    const unsigned bits = spec.width * 16;
    double value = static_cast<double>(raw);
    if (spec.is_signed && (raw & (std::uint64_t{1} << (bits - 1)))) {
        const std::uint64_t mask = bits == 64 ? std::numeric_limits<std::uint64_t>::max() : (std::uint64_t{1} << bits) - 1;
        const auto magnitude = ((~raw) & mask) + 1;
        if (magnitude > (std::uint64_t{1} << 53)) return {0, Quality::Invalid};
        value = -static_cast<double>(magnitude);
    } else if (raw > (std::uint64_t{1} << 53)) return {0, Quality::Invalid}; // Use exact raw decoder for 64-bit counters.
    const double scaled = value * spec.scale;
    return std::isfinite(scaled) ? Value{scaled, Quality::Good} : Value{0, Quality::Invalid};
}
FirmwareVersion decode_firmware(std::uint16_t xxyy, std::uint16_t zz) {
    if (xxyy == 0xFFFF || zz > 255) return {};
    return {static_cast<std::uint8_t>(xxyy >> 8), static_cast<std::uint8_t>(xxyy), static_cast<std::uint8_t>(zz), true};
}
Trip decode_trip(const std::array<std::uint16_t, 6>& words, std::int32_t offset) {
    bool all_unused = true;
    for (auto word : words) all_unused = all_unused && word == 0xFFFF;
    if (all_unused) return {};
    for (auto word : words) if (word == 0xFFFF) return {false, Quality::Invalid, 0, 0, 0, 0};
    const auto hour = words[4] >> 8, minute = words[4] & 255;
    if (hour > 23 || minute > 59 || words[5] > 59 || std::abs(static_cast<std::int64_t>(offset)) > 14 * 3600)
        return {false, Quality::Invalid, 0, 0, 0, 0};
    const auto stamp = static_cast<std::int64_t>(words[3]) * 86400 + hour * 3600 + minute * 60 + words[5] - offset;
    return {true, Quality::Good, static_cast<std::uint16_t>(words[0] & 0x7FFF),
            static_cast<std::uint16_t>(words[1] & 0x7FFF), static_cast<std::uint16_t>(words[2] & 7), stamp};
}
bool UtcClock::synchronize(std::int64_t utc_ms, std::uint64_t mono) {
    bool backwards = false;
    if (anchored_) {
        if (mono < monotonic_ms_ || mono - monotonic_ms_ > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())) backwards = true;
        else {
            const auto elapsed = static_cast<std::int64_t>(mono - monotonic_ms_);
            backwards = utc_ms_ > std::numeric_limits<std::int64_t>::max() - elapsed || utc_ms < utc_ms_ + elapsed;
        }
    }
    if (utc_ms <= 0 || backwards) {
        valid_ = false;
        return false;
    }
    utc_ms_ = utc_ms; monotonic_ms_ = mono; valid_ = true; anchored_ = true;
    return true;
}
bool UtcClock::now(std::uint64_t mono, std::int64_t& utc_ms) const {
    if (!valid_ || mono < monotonic_ms_ || mono - monotonic_ms_ > kMaxHoldoverMs ||
        utc_ms_ > std::numeric_limits<std::int64_t>::max() - static_cast<std::int64_t>(mono - monotonic_ms_)) return false;
    utc_ms = utc_ms_ + static_cast<std::int64_t>(mono - monotonic_ms_);
    return true;
}
std::uint64_t Backoff::fail(std::uint64_t now_ms) {
    state_ ^= state_ << 13; state_ ^= state_ >> 17; state_ ^= state_ << 5;
    const std::uint64_t base = std::min<std::uint64_t>(30000, 500u << std::min<std::uint32_t>(attempts_, 6));
    const std::uint64_t delay = std::min<std::uint64_t>(30000, base + state_ % (base / 4 + 1));
    if (attempts_ < 32) ++attempts_;
    due_ms_ = now_ms > std::numeric_limits<std::uint64_t>::max() - delay ? std::numeric_limits<std::uint64_t>::max() : now_ms + delay;
    return due_ms_;
}

bool PersistentQueue::begin(const char* device) {
    healthy_ = false;
    if (!identifier(device)) return false;
    const std::size_t length = journal_.load(buffer_.data(), buffer_.size());
    if (length > buffer_.size()) return false;
    if (length) {
        if (!restore(length) || std::strcmp(state_.owner.data(), device)) return false;
        healthy_ = true;
        return true;
    }
    candidate_ = State{};
    std::snprintf(candidate_.owner.data(), candidate_.owner.size(), "%s", device);
    return save_candidate();
}
bool PersistentQueue::enqueue(const Frame& frame) {
    if (!healthy_ || frame.sequence != state_.next_sequence || !frame.sequence ||
        state_.next_sequence == std::numeric_limits<std::uint64_t>::max() || frame.utc_ms <= 0 ||
        !std::memchr(frame.payload.data(), 0, frame.payload.size()) || frame.payload[0] != '{' ||
        !std::memchr(frame.message_id.data(), 0, frame.message_id.size())) return false;
    char expected[96]{};
    if (!format_id(expected, sizeof expected, state_.owner.data(), frame.sequence) || std::strcmp(expected, frame.message_id.data())) return false;
    candidate_ = state_;
    if (candidate_.count == kQueueCapacity) {
        if (candidate_.dropped != std::numeric_limits<std::uint64_t>::max()) ++candidate_.dropped;
        save_candidate();
        return false; // Preserve the oldest observations; report rejected newest observation.
    }
    candidate_.frames[candidate_.count++] = frame;
    ++candidate_.next_sequence;
    return save_candidate();
}
bool PersistentQueue::acknowledge(std::uint64_t sequence) {
    if (!healthy_ || !state_.count || state_.frames[0].sequence != sequence) return false;
    candidate_ = state_;
    for (std::size_t i = 1; i < candidate_.count; ++i) candidate_.frames[i - 1] = candidate_.frames[i];
    candidate_.frames[--candidate_.count] = Frame{};
    return save_candidate();
}
bool PersistentQueue::save_candidate() {
    std::size_t cursor = 0;
    auto bytes = [&](const void* source, std::size_t count) { std::memcpy(buffer_.data() + cursor, source, count); cursor += count; };
    auto integer = [&](std::uint64_t value, unsigned width) { for (unsigned i = width; i > 0; --i) buffer_[cursor++] = static_cast<std::uint8_t>(value >> ((i - 1) * 8)); };
    bytes("GSF2", 4); bytes(candidate_.owner.data(), 32);
    integer(candidate_.next_sequence, 8); integer(candidate_.dropped, 8); integer(candidate_.count, 2);
    for (std::size_t i = 0; i < candidate_.count; ++i) {
        const Frame& frame = candidate_.frames[i];
        integer(frame.sequence, 8); integer(static_cast<std::uint64_t>(frame.utc_ms), 8);
        bytes(frame.message_id.data(), frame.message_id.size()); bytes(frame.payload.data(), frame.payload.size());
    }
    integer(modbus_crc16(buffer_.data(), cursor), 2);
    if (!journal_.commit(buffer_.data(), cursor)) { healthy_ = false; return false; }
    state_ = candidate_; healthy_ = true;
    return true;
}
bool PersistentQueue::restore(std::size_t length) {
    constexpr std::size_t base_size = 4 + 32 + 8 + 8 + 2 + 2;
    constexpr std::size_t frame_size = 8 + 8 + 96 + kPayloadCapacity;
    if (length < base_size || std::memcmp(buffer_.data(), "GSF2", 4) ||
        modbus_crc16(buffer_.data(), length - 2) != static_cast<std::uint16_t>((buffer_[length - 2] << 8) | buffer_[length - 1])) return false;
    std::size_t cursor = 4;
    auto bytes = [&](void* destination, std::size_t count) { std::memcpy(destination, buffer_.data() + cursor, count); cursor += count; };
    auto integer = [&](unsigned width) { std::uint64_t value = 0; for (unsigned i = 0; i < width; ++i) value = (value << 8) | buffer_[cursor++]; return value; };
    candidate_ = State{};
    bytes(candidate_.owner.data(), 32);
    if (!std::memchr(candidate_.owner.data(), 0, 32) || !identifier(candidate_.owner.data())) return false;
    candidate_.next_sequence = integer(8); candidate_.dropped = integer(8); candidate_.count = static_cast<std::uint16_t>(integer(2));
    if (!candidate_.next_sequence || candidate_.count > kQueueCapacity || length != base_size + candidate_.count * frame_size) return false;
    std::uint64_t previous = 0;
    for (std::size_t i = 0; i < candidate_.count; ++i) {
        Frame& frame = candidate_.frames[i];
        frame.sequence = integer(8); const auto timestamp = integer(8);
        if (!timestamp || timestamp > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())) return false;
        frame.utc_ms = static_cast<std::int64_t>(timestamp);
        bytes(frame.message_id.data(), frame.message_id.size()); bytes(frame.payload.data(), frame.payload.size());
        char expected[96]{};
        if (frame.sequence <= previous || frame.sequence >= candidate_.next_sequence ||
            !std::memchr(frame.message_id.data(), 0, frame.message_id.size()) ||
            !std::memchr(frame.payload.data(), 0, frame.payload.size()) || frame.payload[0] != '{' ||
            !format_id(expected, sizeof expected, candidate_.owner.data(), frame.sequence) ||
            std::strcmp(expected, frame.message_id.data())) return false;
        previous = frame.sequence;
    }
    state_ = candidate_;
    return true;
}

Runtime::Runtime(Config config, PersistentQueue& queue, UtcClock& clock, ModbusReader& modbus,
                 WirelessReceiver& wireless, MqttPublisher& mqtt, Watchdog& watchdog)
    : config_(config), queue_(queue), clock_(clock), modbus_(modbus), wireless_(wireless), mqtt_(mqtt),
      watchdog_(watchdog), backoff_(identity_seed(config.device_id)) {}
bool Runtime::boot() {
    constexpr std::uint8_t crc_test[]{1, 3, 0, 0, 0, 2};
    health_.boot_ok = valid_config(config_) && config_.source == modbus_.source() &&
        modbus_crc16(crc_test, sizeof crc_test) == 0x0BC4 && queue_.begin(config_.device_id);
    health_.storage_ok = health_.boot_ok;
    return health_.boot_ok;
}
void Runtime::tick(std::uint64_t mono) {
    if (!health_.boot_ok) return;
    std::int64_t utc_ms = 0;
    health_.time_valid = clock_.now(mono, utc_ms);
    if (mono >= next_poll_ms_) {
        if (health_.time_valid && queue_.healthy()) sample(mono, utc_ms);
        next_poll_ms_ = mono > std::numeric_limits<std::uint64_t>::max() - config_.poll_interval_ms ?
            std::numeric_limits<std::uint64_t>::max() : mono + config_.poll_interval_ms;
    }
    if (config_.mqtt_enabled && queue_.healthy() && queue_.front() && backoff_.due(mono)) {
        if (!connected_) connected_ = mqtt_.connect(config_);
        if (connected_) {
            char topic[96]{};
            std::snprintf(topic, sizeof topic, "gridsentinel/telemetry/%s", config_.device_id);
            const Frame* frame = queue_.front();
            if (mqtt_.publish(topic, *frame, 1) == PublishResult::Acknowledged) {
                if (queue_.acknowledge(frame->sequence)) backoff_.success();
            } else { connected_ = false; ++health_.publish_retries; backoff_.fail(mono); }
        } else { ++health_.publish_retries; backoff_.fail(mono); }
    }
    health_.mqtt_online = connected_;
    health_.storage_ok = queue_.healthy();
    health_.queue_drops = queue_.dropped();
    ++health_.cycles;
    watchdog_.feed(); // Loop progress, including offline/backoff, remains independently observable.
}
void Runtime::sample(std::uint64_t mono, std::int64_t utc_ms) {
    std::array<std::uint16_t, 86> mpr{};
    std::array<std::uint16_t, 2> version_words{};
    std::array<std::uint16_t, 7> state_words{};
    std::array<std::uint16_t, 6> trip_words{};
    std::array<std::uint16_t, 13> diagnostic_words{};
    std::array<std::uint16_t, 4> sensor_words{};
    std::uint16_t installed_modules = 0;
    const bool can_poll = config_.source == modbus_.source() &&
        (config_.hardware_reads_enabled || config_.source == Source::GeneratedSynthetic);
    auto read = [&](std::uint8_t port, std::uint8_t unit, ReadRange range, std::uint16_t* words) {
        return can_poll && modbus_.read(port, unit, ReadFunction::Holding, range, words, config_.timeout_ms);
    };
    health_.mpr_online = read(0, config_.mpr_unit, kMprFastRead, mpr.data());
    const bool have_version = read(1, config_.tvoc_unit, kTvocFirmwareRead, version_words.data());
    FirmwareVersion version{};
    if (have_version) version = decode_firmware(version_words[0], version_words[1]);
    const bool have_state = read(1, config_.tvoc_unit, kTvocStateRead, state_words.data());
    const bool have_trip = read(1, config_.tvoc_unit, kTvocTripRead, trip_words.data());
    const bool have_diagnostics = read(1, config_.tvoc_unit, kTvocDiagnosticsRead, diagnostic_words.data());
    const bool have_modules = read(1, config_.tvoc_unit, kTvocModulesRead, &installed_modules);
    bool have_sensors = false;
    if (version.valid && version.major >= 3) have_sensors = read(1, config_.tvoc_unit, kTvocSensorsRead, sensor_words.data());
    health_.tvoc_online = have_version && version.valid && have_state && have_trip && have_diagnostics && have_modules &&
        (version.major < 3 || have_sensors);
    const Trip trip = have_trip ? decode_trip(trip_words, config_.tvoc_utc_offset_seconds) : Trip{};
    const Value current = mpr_value(mpr, health_.mpr_online, "current_l1", config_.mpr_word_order);
    const Value hz = mpr_value(mpr, health_.mpr_online, "frequency_hz", config_.mpr_word_order);
    const Value thdi = mpr_value(mpr, health_.mpr_online, "thd_current_l1", config_.mpr_word_order);
    const Value thdv = mpr_value(mpr, health_.mpr_online, "thd_voltage_l1", config_.mpr_word_order);
    WirelessObservation wireless = wireless_.latest();
    if (!wireless.identity_validated || !wireless.point || std::strcmp(wireless.point, "TH-A / H1")) {
        wireless.temperature.quality = wireless.humidity.quality = Quality::Invalid;
    } else if (mono < wireless.observed_monotonic_ms) {
        wireless.temperature.quality = wireless.humidity.quality = Quality::Invalid;
    } else if (mono - wireless.observed_monotonic_ms > config_.wireless_stale_ms) {
        wireless.temperature.quality = wireless.humidity.quality = Quality::Stale;
    }
    if (!std::isfinite(wireless.humidity.value) || wireless.humidity.value < 0 || wireless.humidity.value > 100) wireless.humidity.quality = Quality::Invalid;
    if (!std::isfinite(wireless.temperature.value) || wireless.temperature.value < -50 || wireless.temperature.value > 150) wireless.temperature.quality = Quality::Invalid;
    char values[6][32]{};
    numeric(current, values[0], 32); numeric(hz, values[1], 32); numeric(thdi, values[2], 32);
    numeric(thdv, values[3], 32); numeric(wireless.temperature, values[4], 32); numeric(wireless.humidity, values[5], 32);
    char timestamp[40]{}, trip_timestamp[40]{}, state[16]{};
    if (!iso_time(utc_ms, timestamp, sizeof timestamp)) return;
    if (have_state) std::snprintf(state, sizeof state, "%u", state_words[0]);
    else std::snprintf(state, sizeof state, "null");
    if (trip.present) iso_time(trip.utc_seconds * 1000, trip_timestamp, sizeof trip_timestamp);
    char raw[8][32]{};
    numeric({static_cast<double>(installed_modules), have_modules ? Quality::Good : Quality::Missing}, raw[0], 32);
    numeric({static_cast<double>(trip.detector_low), trip.quality}, raw[1], 32);
    numeric({static_cast<double>(trip.detector_high), trip.quality}, raw[2], 32);
    numeric({static_cast<double>(trip.relays), trip.quality}, raw[3], 32);
    for (std::size_t i = 0; i < 4; ++i) numeric({static_cast<double>(sensor_words[i]), have_sensors ? Quality::Good : Quality::Missing}, raw[i + 4], 32);
    Frame frame{};
    frame.sequence = queue_.next_sequence(); frame.utc_ms = utc_ms;
    if (!format_id(frame.message_id.data(), frame.message_id.size(), config_.device_id, frame.sequence)) return;
    const char* source = config_.source == Source::GeneratedSynthetic ? "generated_synthetic" : "device_read_unverified";
    // Raw source bitfields retain meaning; full API normalization is an explicit future live-data seam.
    const int size = std::snprintf(frame.payload.data(), frame.payload.size(),
        "{\"edge_schema_version\":1,\"message_id\":\"%s\",\"device_id\":\"%s\",\"panel_id\":\"%s\","
        "\"timestamp\":\"%s\",\"source\":\"%s\",\"scenario\":\"reference_edge\","
        "\"measurements\":{\"current_l1\":%s,\"frequency_hz\":%s,\"thd_current\":%s,\"thd_voltage\":%s,\"ambient_temperature_c\":%s,\"humidity_pct\":%s},"
        "\"quality\":{\"current_l1\":\"%s\",\"frequency_hz\":\"%s\",\"thd_current\":\"%s\",\"thd_voltage\":\"%s\",\"ambient_temperature_c\":\"%s\",\"humidity_pct\":\"%s\"},"
        "\"communication_ok\":%s,\"arc\":{\"event\":%s,\"system_state\":%s,\"communication_ok\":%s},"
        "\"source_register_metadata\":{\"mapping\":\"source_derived\",\"mpr_word_order_verified\":false,\"tvoc_firmware_known\":%s,"
        "\"tvoc_sensor_words_read\":%s,\"installed_modules\":%s,\"latest_trip_quality\":\"%s\",\"latest_trip_utc\":\"%s\","
        "\"detector_low\":%s,\"detector_high\":%s,\"trip_relays_raw\":%s,\"sensor_status_x2_raw\":%s,\"sensor_status_x3_raw\":%s,"
        "\"ambient_x2_raw\":%s,\"ambient_x3_raw\":%s,\"sensor_interpretation_requires_active_error\":true,\"humidity_point\":\"TH-A / H1\"}}",
        frame.message_id.data(), config_.device_id, config_.panel_id, timestamp, source,
        values[0], values[1], values[2], values[3], values[4], values[5], quality_name(current.quality), quality_name(hz.quality),
        quality_name(thdi.quality), quality_name(thdv.quality), quality_name(wireless.temperature.quality), quality_name(wireless.humidity.quality),
        health_.mpr_online ? "true" : "false", have_state ? ((state_words[0] & 1) ? "true" : "false") : "null", state,
        health_.tvoc_online ? "true" : "false", version.valid ? "true" : "false", have_sensors ? "true" : "false", raw[0],
        quality_name(trip.quality), trip_timestamp, raw[1], raw[2], raw[3], raw[4], raw[5], raw[6], raw[7]);
    if (size > 0 && static_cast<std::size_t>(size) < frame.payload.size()) queue_.enqueue(frame);
}
} // namespace gridsentinel
