// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "AutoBiosPolicy.h"
#include "AutoBiosIdentity.h"
#include "Config.h"
#include "GameList.h"
#include "VMManager.h"
#include "ps2/BiosTools.h"
#include "common/Console.h"
#include "common/FileSystem.h"
#include "common/Path.h"
#include <map>

namespace AutoBios
{
inline bool Enabled()
{
    return FileSystem::FileExists(Path::Combine(EmuFolders::AppRoot,
        "custom-pcsx2/auto-bios.enabled").c_str());
}
inline Region FromGameRegion(GameList::Region region)
{
    using R = GameList::Region;
    switch (region)
    {
    case R::NTSC_J: return Region::Japan;
    case R::NTSC_U: case R::NTSC_B: return Region::America;
    case R::NTSC_C: return Region::China;
    case R::NTSC_HK: case R::NTSC_K: case R::NTSC_T: return Region::Asia;
    case R::PAL_A: case R::PAL_AU: case R::PAL_AF: case R::PAL_BE:
    case R::PAL_E: case R::PAL_F: case R::PAL_FI: case R::PAL_G:
    case R::PAL_GR: case R::PAL_I: case R::PAL_IN: case R::PAL_M:
    case R::PAL_NL: case R::PAL_NO: case R::PAL_P: case R::PAL_PL:
    case R::PAL_R: case R::PAL_S: case R::PAL_SC: case R::PAL_SW:
    case R::PAL_SWI: case R::PAL_UK: return Region::Europe;
    case R::Other: case R::Count: return Region::Unknown;
    }
    return Region::Unknown;
}

// Same accepted pre-BIOS hook: scanner cancelled, CDVD locked, real source not yet set.
inline Game DetectGame(const VMBootParameters& boot)
{
    if (boot.filename.empty() || !boot.elf_override.empty() ||
        (boot.source_type && *boot.source_type != CDVD_SourceType::Iso) ||
        !VMManager::IsDiscFileName(boot.filename)) return {};
    auto convert = [&](const GameList::Entry& e) {
        return Game{FromGameRegion(e.region), e.serial, e.crc,
            boot.fast_boot.value_or(static_cast<bool>(EmuConfig.EnableFastBoot))};
    };
    FILESYSTEM_STAT_DATA sd;
    const bool have_stat = FileSystem::StatFile(boot.filename.c_str(), &sd);
    {
        const auto lock = GameList::GetLock();
        if (const auto* entry = GameList::GetEntryForPath(boot.filename.c_str());
            entry && entry->type == GameList::EntryType::PS2Disc && have_stat &&
            entry->total_size == static_cast<u64>(sd.Size) && entry->last_modified_time == sd.ModificationTime)
            return convert(*entry);
    }
    GameList::Entry entry;
    if (!GameList::PopulateEntryFromPath(boot.filename, &entry) || entry.type != GameList::EntryType::PS2Disc)
        return {};
    return convert(entry);
}
struct CatalogueEntry { std::string romver, classification; };
using Catalogue = std::map<std::string, CatalogueEntry>;
inline std::string DataPath(const char* file)
{
    return Path::Combine(Path::Combine(EmuFolders::AppRoot, "custom-pcsx2"), file);
}
inline Catalogue LoadCatalogue()
{
    Catalogue result;
    auto text = FileSystem::ReadFileToString(DataPath("bios-catalogue.tsv").c_str());
    if (!text) { Console.Warning("Auto BIOS TEST: catalogue missing; only content metadata available."); return result; }
    if (text->compare(0,3,"\xef\xbb\xbf")==0) text->erase(0,3);
    std::istringstream stream(*text); std::string line;
    while (std::getline(stream,line))
    {
        if(!line.empty() && line.back()=='\r') line.pop_back();
        if(line.empty() || line.front()=='#') continue;
        const auto f=Fields(line);
        if(f.size()!=4 || !IsHex(f[0],40) ||
           (f[2]!="retail" && f[2]!="special" && f[2]!="early" && f[2]!="auxiliary"))
        { Console.Warning("Auto BIOS TEST: invalid catalogue; ignoring entire catalogue."); return {}; }
        const std::string hash=Lower(f[0]);
        if(!result.emplace(hash,CatalogueEntry{f[1],f[2]}).second)
        { Console.Warning("Auto BIOS TEST: duplicate catalogue identity; ignoring entire catalogue."); return {}; }
    }
    return result;
}
inline Candidate Inspect(const std::string& path, const Catalogue& catalogue)
{
    Candidate c; c.path=path;
    FILESYSTEM_STAT_DATA stat;
    if(path.empty() || !FileSystem::StatFile(path.c_str(), &stat) || stat.Size < 512*1024 || stat.Size > 8*1024*1024)
        return c;
    struct Cached { u64 size; std::time_t modified; Candidate value; };
    // Emulation-thread-only cache. Rules/classification are reapplied each launch.
    static std::map<std::string,Cached> cache;
    const auto found=cache.find(path);
    if(found!=cache.end() && found->second.size==static_cast<u64>(stat.Size) && found->second.modified==stat.ModificationTime)
        c=found->second.value;
    else
    {
        const auto bytes=FileSystem::ReadBinaryFile(path.c_str());
        if(!bytes) return c;
        c.sha1=Hash(*bytes); c.romver=ReadRomver(*bytes);
        u32 region=0; std::string description, zone;
        if(!c.romver.empty() && IsBIOS(path.c_str(), c.version, description, region, zone)) c.region=FromBiosZone(zone);
        cache[path]={static_cast<u64>(stat.Size),stat.ModificationTime,c};
    }
    const auto entry=catalogue.find(c.sha1);
    c.verified=entry!=catalogue.end();
    c.classification=c.verified?entry->second.classification:"uncatalogued";
    const bool headerOK=c.romver.size()==14 && c.romver[5]=='C' && c.region!=Region::Unknown;
    const bool metadataOK=!c.verified || entry->second.romver==c.romver;
    // Unknown full-sized retail-looking images are last-resort candidates, never preferences by version.
    c.eligible=headerOK && metadataOK && stat.Size==4*1024*1024 && c.version>0x0101 &&
        (!c.verified || c.classification=="retail");
    return c;
}
inline std::string Resolve(const VMBootParameters& boot)
{
    const Game game=DetectGame(boot);
    const std::string configured=EmuConfig.FullpathToBios();
    if(game.region==Region::Unknown)
    {
        Console.WriteLn("Auto BIOS TEST: unknown region / BIOS-only boot; configured BIOS '%s'.",configured.c_str());
        return configured;
    }
    const auto catalogue=LoadCatalogue();
    std::vector<Rule> rules;
    const auto text=FileSystem::ReadFileToString(DataPath("bios-rules.tsv").c_str());
    if(!text || !ParseRules(*text,rules)) Console.Warning("Auto BIOS TEST: rules missing/invalid; using conservative region fallback.");
    const auto selected=Inspect(configured,catalogue);
    FileSystem::FindResultsArray files; std::vector<Candidate> candidates;
    if(FileSystem::FindFiles(EmuFolders::Bios.c_str(),"*",FILESYSTEM_FIND_FILES,&files))
        for(const auto& file:files)
        {
            if(file.Size<512*1024 || file.Size>8*1024*1024) continue;
            auto c=Inspect(file.FileName,catalogue);
            if(!c.eligible) Console.WriteLn("Auto BIOS TEST: excluded '%s' (%s, ROMVER %s).",c.path.c_str(),c.classification.c_str(),c.romver.c_str());
            candidates.push_back(std::move(c));
        }
    const auto decision=Select(game,selected,std::move(candidates),rules);
    const auto chosen=Inspect(decision.path,catalogue);
    Console.WriteLn("Auto BIOS TEST: game=%s CRC=%08X boot=%s; %s; path='%s'; ROMVER=%s SHA1=%s.",
        game.serial.c_str(), game.crc, game.fast?"fast":"full",decision.reason.c_str(),
        decision.path.c_str(),chosen.romver.c_str(),chosen.sha1.c_str());
    if(decision.avoidedFallback) Console.Warning("Auto BIOS TEST: fallback has a known game-specific failure; preferred BIOS unavailable.");
    return decision.path;
}
}
