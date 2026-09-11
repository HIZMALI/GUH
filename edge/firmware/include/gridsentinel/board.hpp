#pragma once
#include <cstdint>
namespace gridsentinel::board {
// GPIO numbers, NOT module pad numbers. Source: ESP32-S3-WROOM-1/1U v1.8 pp11-12.
// Reference carrier v0.1 only; no physical GPIO is configured by this header.
struct RtuPins { std::uint8_t tx, rx, de_re; };
inline constexpr RtuPins kMpr{17, 18, 15};
inline constexpr RtuPins kTvoc{4, 5, 6};
inline constexpr std::uint8_t kSpiMosi = 11, kSpiMiso = 13, kSpiClock = 12;
inline constexpr std::uint8_t kEthCs = 10, kEthInterrupt = 9, kEthReset = 14;
inline constexpr std::uint8_t kNvmCs = 21, kWatchdogFeed = 7, kPdFeatureReceive = 2;
inline constexpr std::uint8_t kUsbPlus = 20, kUsbMinus = 19, kLocalBoot = 0;
static_assert(kMpr.tx != kTvoc.tx && kMpr.rx != kTvoc.rx && kMpr.de_re != kTvoc.de_re);
static_assert(kNvmCs != kEthCs); // Independent select lines on the shared SPI bus.
} // namespace gridsentinel::board
