"""Build a compact facts-only snapshot; no scraped descriptions are shipped."""
import argparse
from collections import defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
import yaml
from rules import key

ROOT=Path(__file__).resolve().parent
INDEX_SHA='6589964b54348a4af845bb33311375fa1596c55864be750e9fbdc69c8d7dcdcd'
FACTS_SHA='9f05f6938058d86b66cf3ee54d3b0b157f681c6fc14fb9bacb417edd68cd4b09'

def prepare(index_path,facts_path):
    index_raw=index_path.read_bytes().replace(b'\r\n',b'\n')
    facts_raw=facts_path.read_bytes()
    assert hashlib.sha256(index_raw).hexdigest()==INDEX_SHA,'Unreviewed GameIndex'
    assert hashlib.sha256(facts_raw).hexdigest()==FACTS_SHA,'Unreviewed metadata input'
    index=yaml.safe_load(index_raw)
    facts=defaultdict(list)
    for block in re.split(r'^game \(\s*$',facts_raw.decode('utf-8-sig'),flags=re.M)[1:]:
        values=dict(re.findall(r'^\t([a-z]+) "(.*)"$',block,flags=re.M))
        if values.get('serial'):facts[values['serial']].append(values)
    records=[];rejected=[];matched=0
    for serial,e in index.items():
        row={'serial':serial,'name':e['name'],'english_name':e.get('name-en',''),'region':e.get('region',''),'database_sort':e.get('name-sort','')}
        choices=facts.get(serial,[])
        if len(choices)>1:
            rejected.append({'serial':serial,'reason':'duplicate metadata serial','names':[v.get('name','') for v in choices]})
        elif choices:
            v=choices[0]
            if key(v.get('name','')) not in {key(e['name']),key(e.get('name-en',''))}:
                rejected.append({'serial':serial,'reason':'metadata title does not match GameIndex','metadata_title':v.get('name'),'index_title':e.get('name-en') or e['name']})
            else:
                try:
                    d=date(int(v['releaseyear']),int(v['releasemonth']),int(v['releaseday']))
                    if not 1999<=d.year<=2026:raise ValueError('Outside reviewed PS2 range')
                    row['facts']={'date':d.isoformat(),'developer':v.get('developer',''),'publisher':v.get('publisher',''),'source_serial':serial}
                    matched+=1
                except (KeyError,ValueError):rejected.append({'serial':serial,'reason':'missing or invalid release date'})
        records.append(row)
    snapshot={'schema':1,'index_sha256':INDEX_SHA,'facts_sha256':FACTS_SHA,'records':records}
    payload=json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).encode()
    (ROOT/'identity-metadata.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    report={'schema':1,'identities':len(records),'matched_fact_records':matched,'metadata_limit':'Title-checked facts, not independent historical verification. Conflicting/missing facts are excluded; reviewed franchise metadata overrides inaccurate dates.','sources':{'index':'https://github.com/PCSX2/pcsx2/blob/e35cb2c87590bc3d127b3bb4dd222b01e598c9a4/bin/resources/GameIndex.yaml','facts':'https://github.com/libretro/libretro-database/blob/12c21cf79f1e20eff6ac68b80875816c717d0a7a/metadat/developer/Sony%20-%20PlayStation%202.dat'},'input_sha256':{'index':INDEX_SHA,'facts':FACTS_SHA},'snapshot_sha256':hashlib.sha256((ROOT/'identity-metadata.json.gz').read_bytes()).hexdigest(),'rejected_metadata':rejected}
    (ROOT/'METADATA-PROVENANCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='rejected_metadata'},indent=2));print('Rejected metadata records:',len(rejected))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('gameindex',type=Path);p.add_argument('facts',type=Path);a=p.parse_args();prepare(a.gameindex,a.facts)
