// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <string>
#include <string_view>

// Shared by the stable and nightly experiments. Keep automatic defaults out of
// the user's override file: a rescan/catalogue update must never become an edit.
namespace AutoSortTitle
{
// Compare whole digit runs, never floating point: 7 < 10 < 10.1 < 10.2 < 11.
// Non-numeric runs retain the UI's locale-aware comparator. Large numbers cannot
// overflow; leading zeroes use the full title as a deterministic final tie-break.
template<typename TextCompare>
int Compare(std::string_view left, std::string_view right, TextCompare text_compare)
{
    const auto digit = [](char ch) { return ch >= '0' && ch <= '9'; };
    size_t a = 0, b = 0;
    while (a < left.size() && b < right.size())
    {
        if (digit(left[a]) && digit(right[b]))
        {
            size_t ae = a, be = b;
            while (ae < left.size() && digit(left[ae])) ++ae;
            while (be < right.size() && digit(right[be])) ++be;
            while (a < ae && left[a] == '0') ++a;
            while (b < be && right[b] == '0') ++b;
            if (ae - a != be - b) return ae - a < be - b ? -1 : 1;
            const int cmp = left.substr(a, ae - a).compare(right.substr(b, be - b));
            if (cmp != 0) return cmp;
            a = ae;
            b = be;
        }
        else
        {
            size_t ae = a + 1, be = b + 1;
            while (ae < left.size() && !digit(left[ae])) ++ae;
            while (be < right.size() && !digit(right[be])) ++be;
            const int cmp = text_compare(left.substr(a, ae - a), right.substr(b, be - b));
            if (cmp != 0) return cmp;
            a = ae;
            b = be;
        }
    }
    if (a != left.size() || b != right.size()) return a == left.size() ? -1 : 1;
    return text_compare(left, right);
}

inline const std::string& Resolve(const std::string& manual, bool normal,
    const std::string& automatic, const std::string& title,
    const std::string& database_sort, const std::string& english, bool prefer_english)
{
    if (!manual.empty())
        return manual;
    if (!normal && !automatic.empty())
        return automatic;
    if (prefer_english && !english.empty())
        return english;
    return database_sort.empty() ? title : database_sort;
}
}
