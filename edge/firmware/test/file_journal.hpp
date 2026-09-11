#pragma once
#include "gridsentinel/core.hpp"
#include <cerrno>
#include <cstring>
#include <filesystem>
#include <limits>
#include <string>
#include <fcntl.h>
#include <unistd.h>

// POSIX host test implementation. This does NOT implement ESP-IDF NVS or prove flash endurance.
class FileJournal final : public gridsentinel::Journal {
 public:
    explicit FileJournal(std::string path) : path_(std::move(path)) {}
    std::size_t load(std::uint8_t* destination, std::size_t capacity) override {
        const int fd = ::open(path_.c_str(), O_RDONLY);
        if (fd < 0) return errno == ENOENT ? 0 : capacity + 1;
        std::size_t count = 0;
        while (count < capacity) {
            const auto n = ::read(fd, destination + count, capacity - count);
            if (n < 0 && errno == EINTR) continue;
            if (n < 0) { ::close(fd); return capacity + 1; }
            if (!n) break;
            count += static_cast<std::size_t>(n);
        }
        std::uint8_t extra = 0;
        const auto tail = ::read(fd, &extra, 1);
        ::close(fd);
        // A present empty file is corrupt, not a new identity with reset sequence.
        return !count || tail != 0 ? capacity + 1 : count;
    }
    bool commit(const std::uint8_t* data, std::size_t length) override {
        const auto temporary = path_ + ".pending";
        const int fd = ::open(temporary.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
        if (fd < 0) return false;
        std::size_t count = 0;
        while (count < length) {
            const auto n = ::write(fd, data + count, length - count);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) { ::close(fd); return false; }
            count += static_cast<std::size_t>(n);
        }
        const bool synced = ::fsync(fd) == 0;
        const bool closed = ::close(fd) == 0;
        if (!synced || !closed || ::rename(temporary.c_str(), path_.c_str())) return false;
        const auto parent = std::filesystem::path(path_).parent_path().string();
        const int directory = ::open(parent.empty() ? "." : parent.c_str(), O_RDONLY | O_DIRECTORY);
        if (directory < 0) return false;
        const bool durable = ::fsync(directory) == 0;
        ::close(directory);
        return durable;
    }
 private:
    std::string path_;
};
