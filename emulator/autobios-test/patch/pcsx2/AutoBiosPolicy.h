// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <algorithm>
#include <cstdint>
#include <sstream>
#include <string>
#include <vector>

namespace AutoBios
{
enum class Region { Unknown, Japan, America, Europe, Asia, China };
inline Region FromBiosZone(const std::string& z)
{
    if(z=="Japan") return Region::Japan;
    if(z=="USA") return Region::America;
    if(z=="Europe") return Region::Europe;
    if(z=="Asia") return Region::Asia;
    if(z=="China") return Region::China;
    return Region::Unknown;
}
struct Game { Region region=Region::Unknown; std::string serial; std::uint32_t crc=0; bool fast=false; };
struct Candidate
{
    std::string path;
    Region region=Region::Unknown;
    std::uint32_t version=0;
    std::string sha1, romver, classification;
    bool eligible=false, verified=false;
};
struct Rule
{
    bool avoid=false;
    Region region=Region::Unknown;
    std::string serial;
    std::uint32_t crc=0;
    std::string boot, sha1, reason;
};
struct Decision { std::string path, reason; bool avoidedFallback=false; };
inline bool IsHex(const std::string& s, std::size_t size)
{
    return s.size()==size && std::all_of(s.begin(),s.end(),[](char c) {
        return (c>='0' && c<='9') || (c>='a' && c<='f') || (c>='A' && c<='F'); });
}
inline std::string Lower(std::string s)
{
    for(auto& c:s) if(c>='A' && c<='Z') c=static_cast<char>(c-'A'+'a');
    return s;
}
inline std::vector<std::string> Fields(const std::string& line)
{
    std::vector<std::string> out;
    std::size_t start=0, end;
    while ((end=line.find('\t',start))!=std::string::npos) { out.push_back(line.substr(start,end-start)); start=end+1; }
    out.push_back(line.substr(start)); return out;
}
inline bool ParseRules(std::string text, std::vector<Rule>& rules)
{
    // All-or-nothing parsing: malformed rules never leave a partial policy active.
    rules.clear(); std::vector<Rule> parsed;
    if(text.compare(0,3,"\xef\xbb\xbf")==0) text.erase(0,3);
    std::istringstream stream(text); std::string line;
    while(std::getline(stream,line))
    {
        if(!line.empty() && line.back()=='\r') line.pop_back();
        if(line.empty() || line.front()=='#') continue;
        const auto f=Fields(line);
        if(f.size()!=7 || (f[0]!="prefer" && f[0]!="avoid") ||
           FromBiosZone(f[1])==Region::Unknown || !IsHex(f[5],40) ||
           (f[4]!="any" && f[4]!="full" && f[4]!="fast")) return false;
        const bool regional=f[2]=="*";
        if((regional && f[3]!="*") || (!regional && (f[2].empty() || !IsHex(f[3],8))) ||
            (regional && f[0]=="avoid")) return false;
        Rule r; r.avoid=f[0]=="avoid"; r.region=FromBiosZone(f[1]); r.serial=f[2];
        if(!regional) r.crc=static_cast<std::uint32_t>(std::stoul(f[3],nullptr,16));
        r.boot=f[4]; r.sha1=Lower(f[5]); r.reason=f[6]; parsed.push_back(std::move(r));
    }
    rules=std::move(parsed); return true;
}
inline bool Matches(const Rule& r, const Game& game)
{
    return r.region==game.region && (r.serial=="*" || (r.serial==game.serial && r.crc==game.crc)) &&
        (r.boot=="any" || (r.boot=="fast")==game.fast);
}
inline bool Avoided(const Candidate& c,const Game& g,const std::vector<Rule>& rules)
{
    return std::any_of(rules.begin(),rules.end(),[&](const Rule& r){return r.avoid && Matches(r,g) && r.sha1==c.sha1;});
}
inline Decision Select(const Game& game,const Candidate& selected,std::vector<Candidate> candidates,const std::vector<Rule>& rules)
{
    if(game.region==Region::Unknown) return {selected.path,"unknown game region / BIOS-only boot; configured BIOS"};
    candidates.push_back(selected);
    candidates.erase(std::remove_if(candidates.begin(),candidates.end(),[&](const Candidate& c){
        return !c.eligible || c.region!=game.region || Avoided(c,game,rules); }),candidates.end());
    // This tie-break is stable identity order, explicitly NOT a compatibility ranking.
    std::sort(candidates.begin(),candidates.end(),[](const Candidate& a,const Candidate& b){
        if(a.verified!=b.verified) return a.verified>b.verified;
        if(a.sha1!=b.sha1) return a.sha1<b.sha1;
        return a.path<b.path;
    });
    for(bool regional : {false,true})
        for(const auto& r:rules)
            if(!r.avoid && (r.serial=="*")==regional && Matches(r,game))
                for(const auto& c:candidates)
                    if(c.sha1==r.sha1) return {c.path,(regional?"regional preference: ":"game preference: ")+r.reason};
    if(selected.eligible && selected.region==game.region && !Avoided(selected,game,rules))
        return {selected.path,"eligible configured BIOS matches region"};
    if(!candidates.empty()) return {candidates.front().path,"matching-region fallback (stable hash order, not compatibility ranked)"};
    return {selected.path,"no eligible matching-region BIOS; configured fallback",Avoided(selected,game,rules)};
}
}
