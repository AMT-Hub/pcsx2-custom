// SPDX-License-Identifier: GPL-3.0-or-later
#include "../AutoSortTitle.h"
#include <algorithm>
#include <cassert>
#include <vector>

int main()
{
    const std::string title = "TimeSplitters - Future Perfect";
    const std::string database = "Database title", english = "English title";
    const std::string automatic = "TimeSplitters 3", manual = "My edited title", empty;
    using AutoSortTitle::Resolve;
    assert(Resolve(manual, false, automatic, title, database, english, true) == manual);
    assert(Resolve(manual, true, automatic, title, database, english, true) == manual);
    assert(Resolve(empty, false, automatic, title, database, english, true) == automatic);
    assert(Resolve(empty, true, automatic, title, database, english, false) == database);
    assert(Resolve(empty, true, automatic, title, database, english, true) == english);
    assert(Resolve(empty, true, automatic, title, empty, empty, false) == title);
    assert(Resolve(empty, false, empty, title, empty, empty, false) == title);
    assert(title == "TimeSplitters - Future Perfect");

    const auto cmp = [](const std::string& a, const std::string& b) {
        return AutoSortTitle::Compare(a, b, [](std::string_view x, std::string_view y) { return x.compare(y); });
    };
    const std::vector<std::string> ordered = {"Final Fantasy 7", "Final Fantasy 10",
        "Final Fantasy 10.1", "Final Fantasy 10.2", "Final Fantasy 11",
        "Final Fantasy 12", "Final Fantasy 12.1"};
    auto reversed = ordered;
    std::reverse(reversed.begin(), reversed.end());
    std::sort(reversed.begin(), reversed.end(), [&](const auto& a, const auto& b) { return cmp(a, b) < 0; });
    assert(reversed == ordered);
    assert(cmp("Monster Hunter 1", "Monster Hunter 1.1") < 0);
    assert(cmp("Monster Hunter 1.1", "Monster Hunter 2") < 0);
    assert(cmp("Star Wars - Battlefront 0.5", "Star Wars - Battlefront 1") < 0);
    assert(cmp("Game 99999999999999999999", "Game 100000000000000000000") < 0);
    const std::vector<std::string> cases = {"", "1", "01", "0.5", "0.05", "1.1", "2", "10",
        "11", "12.1", "X", "Ico", "Game", "Game 01", "Game 1", "Game 1a", "Game 10", "Game-a"};
    for (const auto& a : cases)
        for (const auto& b : cases)
        {
            assert((cmp(a,b) < 0) == (cmp(b,a) > 0));
            for (const auto& c : cases)
                if (cmp(a,b) < 0 && cmp(b,c) < 0) assert(cmp(a,c) < 0);
        }
}
