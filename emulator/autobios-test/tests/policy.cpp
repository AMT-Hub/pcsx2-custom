#include "../patch/pcsx2/AutoBiosPolicy.h"
#include "../patch/pcsx2/AutoBiosIdentity.h"
#include <cassert>
#include <fstream>
#include <iostream>
using namespace AutoBios;
int main(int argc,char** argv)
{
    if(argc==2) {std::ifstream f(argv[1],std::ios::binary); std::vector<std::uint8_t> b((std::istreambuf_iterator<char>(f)),{}); std::cout<<Hash(b); return 0;}
    assert(Hash({})=="da39a3ee5e6b4b0d3255bfef95601890afd80709");
    assert(Hash({'a','b','c'})=="a9993e364706816aba3e25717850c26c9cd0d89d");
    assert(Hash(std::vector<std::uint8_t>(1000000,'a'))=="34aa973cd4c4daa4f61eeb2bdbad27316534016f");
    assert(ReadRomver({}).empty());
    std::vector<std::uint8_t> rom(256);
    std::memcpy(rom.data()+64,"RESET",5); rom[76]=64;
    std::memcpy(rom.data()+80,"ROMDIR",6); rom[92]=64;
    std::memcpy(rom.data()+96,"ROMVER",6); rom[108]=14;
    std::memcpy(rom.data()+128,"0160AC20020207",14);
    assert(ReadRomver(rom)=="0160AC20020207");
    rom.resize(130); assert(ReadRomver(rom).empty());
    Candidate old{"renamed.bin",Region::America,0x160,std::string(40,'a'),"0160AC20020207","retail",true,true};
    Candidate latest{"new.bin",Region::America,0x230,std::string(40,'b'),"0230AC20080220","retail",true,true};
    Candidate eu{"europe.bin",Region::Europe,0x200,std::string(40,'c'),"0200EC20040614","retail",true,true};
    Candidate dev=latest;dev.path="dev.bin";dev.eligible=false;
    Game jak{Region::America,"SCUS-97124",0x1B3976AB,false};
    std::vector<Rule> rules;
    std::string t="prefer\tUSA\tSCUS-97124\t1B3976AB\tfull\t"+old.sha1+"\tJak test\n";
    assert(ParseRules(t,rules));
    assert(Select(jak,latest,{latest,old,dev},rules).path==old.path);
    auto other=jak;other.crc++; assert(Select(other,latest,{old},rules).path==latest.path);
    auto fast=jak;fast.fast=true; assert(Select(fast,latest,{old},rules).path==latest.path);
    assert(Select(jak,latest,{latest},rules).path==latest.path);
    assert(Select({},latest,{old},rules).path==latest.path);
    assert(Select(jak,eu,{dev,old},rules).path==old.path);
    assert(Select(jak,eu,{dev},rules).path==eu.path);
    t+="avoid\tUSA\tSCUS-97124\t1B3976AB\tfull\t"+latest.sha1+"\tknown failure\n";
    assert(ParseRules(t,rules));
    assert(Select(jak,latest,{latest},rules).avoidedFallback);
    assert(Select(jak,latest,{old},rules).path==old.path);
    assert(Select(fast,latest,{old},rules).path==latest.path);
    t+="prefer\tUSA\t*\t*\tany\t"+old.sha1+"\tprovisional default\n";
    assert(ParseRules(t,rules));assert(Select(other,latest,{old},rules).path==old.path);
    assert(!ParseRules(t+"broken",rules) && rules.empty());
    assert(!ParseRules("avoid\tUSA\t*\t*\tany\t"+old.sha1+"\tinvalid\n",rules));
    assert(Select(jak,eu,{latest,old},{}).path==Select(jak,eu,{old,latest},{}).path);
    assert(Select({Region::Europe,"X",1,false},eu,{old},{}).path==eu.path);
    std::cout<<"All BIOS identity and selection tests passed.\n";
}
