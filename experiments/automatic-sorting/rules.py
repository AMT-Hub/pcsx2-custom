"""Compile offline sorting defaults from the entire PS2 identity database.

Rules are independent of installed ROMs. Curated user exceptions win over
franchise policies, numbered-series inference and safe text normalisation.
"""
from collections import defaultdict
from decimal import Decimal
import re
import unicodedata

ROMAN_VALUES={'I':1,'V':5,'X':10}
ROMAN_PATTERN=re.compile(r'(?<![\w-])([IVX]+)(?![\w-])')
NONRETAIL_TAGS=re.compile(r'demo|trial|beta|prototype|sampler|preview|sample|trade demo|promo',re.I)
REISSUE_TAGS=re.compile(r'greatest hits|platinum|the best|best price|capcolle|classics|ultimate hits|mega hits|ea best hits|ea:sy|dendou|bighit|big hit|thq collection|reprint',re.I)

def key(title):
    text=unicodedata.normalize('NFKC',title).casefold()
    text=re.sub(r'\([^)]*\)$','',text).strip()
    text=re.sub(r'\[[^]]*\]','',text).strip()
    if text.endswith(', the'):text='the '+text[:-5]
    text=re.sub(r'^the\s+','',text)
    return ' '.join(re.sub(r'[^\w]+',' ',text).split())

def retail(serial,title):
    if serial.startswith(('SCED-','SLED-','TLED-','TLES-')) or re.fullmatch(r'SLUS-(28|29)\d{3}',serial):
        return False
    if any(NONRETAIL_TAGS.search(tag) for tag in re.findall(r'\[([^]]+)\]',title)):
        return False
    return not re.search(r'\bDemo(?:nstration)?(?: Disc)?\b|\bBeta Trial Code\b|\bSample(?:r)? Disc\b|\bTrial Version\b',title,re.I)

def edition_base(title):
    # Only reviewed reissue labels disappear; disc/edition distinctions survive.
    return re.sub(r'\s*\[([^]]+)\]',lambda m:'' if REISSUE_TAGS.search(m[1]) else m[0],title).strip()

def roman_number(token):
    # Canonical spellings only; reject words, subtractive errors and large tokens.
    if not re.fullmatch(r'X{0,3}(IX|IV|V?I{0,3})',token) or not token:return None
    total=0
    for i,ch in enumerate(token):
        value=ROMAN_VALUES[ch]
        total+=-value if i+1<len(token) and value<ROMAN_VALUES[token[i+1]] else value
    return total

def normalise_title(title,policy):
    title=unicodedata.normalize('NFKC',title).strip()
    # Stylised digits require semantic aliases; arbitrary substitutions are unsafe.
    for before,after in policy.get('stylised_titles',{}).items():
        if key(title)==key(before):return after
    protected=any(re.match(pattern,title,re.I) for pattern in policy.get('roman_protected_patterns',[]))
    if protected:return title
    def convert(match):
        token=match[1]; number=roman_number(token)
        if number is None:return token
        if token in ('I','V','X'):
            preceding=title[:match.start()].strip()
            if not any(re.fullmatch(pattern,preceding,re.I) for pattern in policy.get('single_roman_contexts',[])):
                return token
        return str(number)
    return ROMAN_PATTERN.sub(convert,title)

def canonical_title(title,policy):
    title=edition_base(title)
    title=policy.get('_aliases',{}).get(key(title),title)
    for before,after in policy.get('canonical_prefixes',{}).items():
        if title.casefold().startswith(before.casefold()):
            title=after+title[len(before):]
            break
    return title

def compile_defaults(records,policy,exceptions):
    policy={**policy,'_aliases':{key(alias):canonical for canonical,aliases in policy.get('regional_aliases',{}).items() for alias in aliases+[canonical]}}
    identities={r['serial']:r for r in records}
    if len(identities)!=len(records):raise ValueError('Duplicate metadata serial')
    output={}; provenance={}; groups=defaultdict(list); titles={}
    for r in records:
        serial=r['serial']; raw=r.get('english_name') or r['name']
        if not retail(serial,raw):continue
        title=canonical_title(raw,policy); titles[serial]=title
        output[serial]=normalise_title(title,policy)
        provenance[serial]='normalised-title' if output[serial]!=raw else 'normal-title'
        groups[key(title)].append(r)
    # Whole-database sibling detection. Adding a ROM cannot renumber its siblings.
    roots={}
    for title in output.values():
        m=re.fullmatch(r'(.+?)\s+([2-9]|[1-9][0-9])(?:\s+-\s+.*)?',title)
        if m:roots[key(m[1])]=m[1]
    for serial,title in list(output.items()):
        if key(title) in roots:
            output[serial]=title+' 1';provenance[serial]='numbered-series-first'
    # An unnumbered first game can have a subtitle. Only infer this when there
    # is exactly one distinct unnumbered candidate and no bare first game.
    for root,display in roots.items():
        if root in groups:continue
        candidates={key(t):t for t in output.values() if t.casefold().startswith(display.casefold()+' - ')}
        if len(candidates)!=1:continue
        candidate=next(iter(candidates))
        for serial,title in list(output.items()):
            if key(title)==candidate:
                output[serial]=display+' 1'+title[len(display):]
                provenance[serial]='numbered-series-first'
    unresolved=[]
    families=list(policy.get('families',[]))
    # Discover other subtitle series across the database, without a per-game list.
    # Require two distinct games and complete identity-checked date metadata.
    inferred=defaultdict(list)
    for game_key,rows in groups.items():
        title=titles[rows[0]['serial']]
        if ' - ' not in title or '[' in title:continue
        prefix=title.split(' - ',1)[0]
        if len(prefix.split())<2 or re.search(r'\d',normalise_title(prefix,policy)):continue
        if any(any(re.search(p,title,re.I) for p in f['patterns']) for f in families):continue
        inferred[prefix].append((game_key,rows))
    for prefix,members in sorted(inferred.items()):
        if len(members)<2:continue
        # Do not treat separate regional aliases as separate instalments. Require
        # every member to exist in a shared region, unless an explicit policy
        # establishes their relationship. Also avoid competing with numbered
        # siblings (e.g. Silent Hill 2 plus the later subtitle-only spin-offs).
        common_regions=set.intersection(*[{r.get('region') for r in rows if r.get('region')} for _,rows in members])
        numbered_siblings=any(re.match('^'+re.escape(prefix)+r'\s+\d',t,re.I) for t in output.values())
        if not common_regions or numbered_siblings:
            unresolved.append({'family':'inferred:'+prefix,'title':prefix,'reason':'regional equivalence or mixed numbered/subtitle series needs explicit metadata','serials':[r['serial'] for _,rows in members for r in rows]})
            continue
        if not all(any(r.get('facts',{}).get('date') for r in rows) for _,rows in members):
            unresolved.append({'family':'inferred:'+prefix,'title':prefix,'reason':'subtitle family needs complete date metadata','serials':[r['serial'] for _,rows in members for r in rows]})
            continue
        families.append({'id':'inferred:'+prefix,'prefix':prefix,'patterns':['^'+re.escape(prefix)+r' - '],'start':1,'keep_subtitle':True,'inferred':True})
    family_claims={}
    for family in families:
        members=[]
        for game_key,rows in groups.items():
            title=titles[rows[0]['serial']]
            if not any(re.search(pattern,title,re.I) for pattern in family['patterns']):continue
            if any(re.search(pattern,title,re.I) for pattern in family.get('exclude_patterns',[])):continue
            # Unknown boxed sets/bonus discs never silently become a new instalment.
            if '[' in title or any(word in title.lower() for word in ('double pack','trilogy','collection','action pack')):continue
            if game_key in family_claims:raise ValueError('Overlapping franchise rules: '+title)
            family_claims[game_key]=family['id']
            facts=[r['facts'] for r in rows if r.get('facts')]
            reviewed=policy.get('reviewed_metadata',{}).get(game_key,{})
            dates=[f['date'] for f in facts if f.get('date')]
            date=reviewed.get('date') or (min(dates) if dates else None)
            devs={f['developer'] for f in facts if f.get('developer')}
            pubs={f['publisher'] for f in facts if f.get('publisher')}
            devs={policy.get('company_aliases',{}).get(d,d) for d in devs}
            pubs={policy.get('company_aliases',{}).get(p,p) for p in pubs}
            developer=reviewed.get('developer') or (sorted(devs)[0] if len(devs)==1 else None)
            publisher=reviewed.get('publisher') or (sorted(pubs)[0] if len(pubs)==1 else None)
            group=developer or publisher if family.get('group_by_developer') else ''
            if not date or (family.get('group_by_developer') and not group):
                unresolved.append({'family':family['id'],'title':title,'reason':'missing/conflicting chronology or developer metadata','serials':[r['serial'] for r in rows]})
                # Keep the franchise grouped even when exact chronology is unknown.
                for r in rows:
                    if not output[r['serial']].casefold().startswith(family['prefix'].casefold()):
                        output[r['serial']]=family['prefix']+' - '+output[r['serial']]
                    provenance[r['serial']]='franchise-unresolved-order'
                continue
            members.append((group,date,game_key,title,rows))
        # Equal or overlapping year/day precision cannot establish chronology.
        ambiguous_groups=set()
        for i,a in enumerate(members):
            for b in members[i+1:]:
                if a[0]==b[0] and (a[1].startswith(b[1]) or b[1].startswith(a[1])):
                    ambiguous_groups.add(a[0])
        for group in sorted(ambiguous_groups):
            affected=[m for m in members if m[0]==group]
            unresolved.append({'family':family['id'],'title':family['prefix'],'reason':'release dates do not establish a unique order','serials':[r['serial'] for m in affected for r in m[4]]})
        members=[m for m in members if m[0] not in ambiguous_groups]
        counters=defaultdict(int)
        for group,date,game_key,title,rows in sorted(members,key=lambda x:(x[0],x[1],x[2])):
            index=counters[group];counters[group]+=1
            position=Decimal(str(family.get('start',1)))+Decimal(str(family.get('step',1)))*index
            number=format(position,'f').rstrip('0').rstrip('.') if '.' in format(position,'f') else str(position)
            value=family['prefix']+(' - '+group if group else '')+' '+number
            if family.get('keep_subtitle'):
                subtitle=re.sub('^'+re.escape(family['prefix'])+r'\s*-?\s*','',normalise_title(title,policy),flags=re.I)
                value+=' - '+subtitle
            for r in rows:output[r['serial']]=value;provenance[r['serial']]='franchise-release-order'
    for serial,value in exceptions.items():
        if serial in output:output[serial]=value;provenance[serial]='user-exception'
    unresolved=[r for r in unresolved if not all(s in exceptions for s in r['serials'])]
    return output,provenance,unresolved
