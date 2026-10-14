// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace AutoBios
{
// SHA-1 is used only for identification against the public BIOS catalogue.
inline std::string Hash(const std::vector<std::uint8_t>& input)
{
    auto data = input;
    const std::uint64_t bits = static_cast<std::uint64_t>(data.size()) * 8;
    data.push_back(0x80);
    while (data.size() % 64 != 56) data.push_back(0);
    for (int i = 7; i >= 0; --i) data.push_back(static_cast<std::uint8_t>(bits >> (i * 8)));
    std::array<std::uint32_t, 5> h{0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476, 0xc3d2e1f0};
    const auto rol = [](std::uint32_t x, int n) { return (x << n) | (x >> (32 - n)); };
    for (std::size_t off = 0; off < data.size(); off += 64)
    {
        std::uint32_t w[80]{};
        for (int i = 0; i < 16; ++i)
            for (int j = 0; j < 4; ++j) w[i] = (w[i] << 8) | data[off + i * 4 + j];
        for (int i = 16; i < 80; ++i) w[i] = rol(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
        auto a=h[0], b=h[1], c=h[2], d=h[3], e=h[4];
        for (int i = 0; i < 80; ++i)
        {
            std::uint32_t f, k;
            if (i < 20) { f = (b & c) | (~b & d); k = 0x5a827999; }
            else if (i < 40) { f = b ^ c ^ d; k = 0x6ed9eba1; }
            else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8f1bbcdc; }
            else { f = b ^ c ^ d; k = 0xca62c1d6; }
            const auto t = rol(a, 5) + f + e + k + w[i];
            e=d; d=c; c=rol(b,30); b=a; a=t;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e;
    }
    std::string result;
    for (auto word : h)
        for (int n = 28; n >= 0; n -= 4) result += "0123456789abcdef"[(word >> n) & 15];
    return result;
}
inline std::string ReadRomver(const std::vector<std::uint8_t>& data)
{
    static constexpr char reset[10] = "RESET";
    for (std::size_t dir = 0; dir + 16 <= data.size(); dir += 16)
    {
        if (std::memcmp(data.data() + dir, reset, 10)) continue;
        std::uint64_t offset = 0;
        for (auto pos = dir; pos + 16 <= data.size(); pos += 16)
        {
            const char* name = reinterpret_cast<const char*>(data.data() + pos);
            if (!name[0] || !std::memchr(name, 0, 10)) break;
            std::uint32_t size = 0;
            for (int j=3; j>=0; --j) size = (size << 8) | data[pos+12+j];
            if (offset + size > data.size()) break;
            if (std::strcmp(name, "ROMVER") == 0 && size >= 14)
            {
                std::string v(reinterpret_cast<const char*>(data.data() + offset), 14);
                bool valid = true;
                for (int i=0; i<14; ++i)
                    valid &= (i==4 || i==5) ? (v[i]>='A' && v[i]<='Z') : (v[i]>='0' && v[i]<='9');
                if (valid) return v;
                break;
            }
            offset += (static_cast<std::uint64_t>(size) + 15) & ~std::uint64_t(15);
        }
    }
    return {};
}
}
