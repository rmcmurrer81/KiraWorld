"""Read cached source identities and preserve a versioned, source-bound case index.

This resolves named facilities for analogy, not facts, dimensions, visual coverage,
or real-place access. Domains and different document URLs never establish cases.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from .world_layout_job import load_research

CONTRACT = 'source_bound_analog_case_index_v1'
REGISTRY = Path(__file__).with_name('reviewed_analog_cases.json')
MIN_CASES = 3
NAME = r"[A-Z][A-Za-z0-9'\u2019&-]*(?:\s+(?:[A-Z][A-Za-z0-9'\u2019&-]*|of|the|and)){0,6}"
FACILITY = re.compile(r'\b('+NAME+r'\s+(?:Mall|Shopping Cent(?:er|re)|Habitat|Research Station|Research Facility|Museum|Hotel|Library|Campus|School|Hospital|Airport))\b')
SUFFIX = re.compile(r'\s+(?:mall|shopping cent(?:er|re)|habitat|research station|research facility|museum|hotel|library|campus|school|hospital|airport)$', re.I)
GENERIC = {'main','space','human','research','our','your','new','official','visitor','example','generic'}
PREFIX = re.compile(r'^(?:(?:Welcome to|About|Visit|Explore|The|Official)\s+)+')


class CaseEvidenceRequired(ValueError):
    pass


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized_name(name):
    # Removing facility-kind synonyms merges conservative aliases. Different
    # same-named locations may undercount; a publisher/domain never splits them.
    name=PREFIX.sub('',name).strip()
    name=SUFFIX.sub('',name)
    return re.sub(r'[^a-z0-9]+','',name.casefold())


def anchor(source,start,end):
    text=source['text']
    if type(start) is not int or type(end) is not int or not 0<=start<end<=len(text):
        raise ValueError('Invalid case identity anchor span')
    return {'source_id':source['source_id'],'text_sha256':source['text_binding']['sha256'],
            'char_start':start,'char_end':end,'quote':text[start:end]}


def names_in(text):
    found=[]
    for match in FACILITY.finditer(text):
        name=PREFIX.sub('',match.group(1)).strip()
        key=normalized_name(name)
        if not key or key in GENERIC:continue
        found.append(name)
    return list(dict.fromkeys(found))


def automatic_identity(source):
    """A named title plus a body mention; multi-place/unknown titles stay unresolved."""
    text=source['text'];title=source.get('title','')
    if not isinstance(title,str) or not text.splitlines() or text.splitlines()[0]!=title:
        return None,'Title is not an exact first-line source-text anchor'
    names=names_in(title)
    if len(names)!=1 or ' and ' in names[0]:
        return None,'Need one explicit named facility in the source title'
    name=names[0];first=text.find(name);second=text.find(name,len(title))
    if first<0 or second<0:
        return None,'Named title needs a matching body identity mention'
    aliases=[name];anchors=[anchor(source,first,first+len(name)),anchor(source,second,second+len(name))]
    # Alias statements are data with exact anchors. Merely mentioning a second
    # place does not create an alias or another case for this document.
    offset=0
    for line in text.splitlines(keepends=True):
        if re.search(r'\b(?:also known as|also called|formerly known as|formerly)\b',line,re.I):
            line_names=names_in(line)
            if name in line_names and len(line_names)==2:
                for other in line_names:
                    if other not in aliases:
                        aliases.append(other);start=offset+line.index(other)
                        anchors.append(anchor(source,start,start+len(other)))
        offset+=len(line)
    return {'case_name':name,'aliases':aliases,'keys':sorted({normalized_name(n) for n in aliases}),
            'anchors':anchors,'basis':'named_title_and_body_anchor'},None


def reviewed_identity(source,entries):
    for entry in entries:
        if entry['source_id']!=source['source_id'] or entry['text_sha256']!=source['text_binding']['sha256']:
            continue
        saved=entry['anchor'];actual=anchor(source,saved['char_start'],saved['char_end'])
        if actual['quote']!=saved['quote']:
            raise ValueError('Reviewed case identity anchor changed')
        aliases=entry['aliases']
        if not aliases or any(not isinstance(a,str) or a.casefold() not in source['text'].casefold() for a in aliases):
            raise ValueError('Reviewed case alias lacks an exact cached name')
        return {'case_name':entry['case_name'],'aliases':aliases,
                'keys':sorted({normalized_name(n) for n in aliases}),
                'anchors':[actual],'basis':'reviewed_existing_source_identity'},None
    return None,None


def resolve_case_index(job_dir):
    """Pure cached-byte resolution. It performs no fetch, model call or write."""
    job_dir=Path(job_dir).resolve()
    packet,packet_sha,brief,sources=load_research(job_dir)
    registry_raw=REGISTRY.read_bytes();registry=json.loads(registry_raw)
    if registry.get('contract')!='reviewed_analog_case_identity_registry_v1' or not isinstance(registry.get('entries'),list):
        raise ValueError('Invalid reviewed analog case registry')
    records=[]
    for source in sources.values():
        identity,error=reviewed_identity(source,registry['entries'])
        if identity is None:identity,error=automatic_identity(source)
        row={'source_id':source['source_id'],'final_url':source['final_url'],
             'source_bindings':{k:copy.deepcopy(source[k]) for k in ('content_binding','text_binding','capture_binding') if k in source}}
        row.update({'state':'resolved','identity':identity} if identity else {'state':'unresolved','reason':error})
        records.append(row)
    # A case is an alias-connected name group, independent of URLs and domains.
    parents={key:key for row in records if row['state']=='resolved' for key in row['identity']['keys']}
    def find(key):
        while parents[key]!=key:
            parents[key]=parents[parents[key]];key=parents[key]
        return key
    for row in records:
        if row['state']!='resolved':continue
        keys=row['identity']['keys']
        for key in keys[1:]:
            a,b=find(keys[0]),find(key)
            if a!=b:parents[max(a,b)]=min(a,b)
    groups={}
    for row in records:
        if row['state']=='resolved':groups.setdefault(find(row['identity']['keys'][0]),[]).append(row)
    cases=[]
    for group,rows in groups.items():
        case_id='case_'+digest({'normalized_name_group':group})[:20]
        for row in rows:row['case_id']=case_id
        cases.append({'case_id':case_id,'case_name':rows[0]['identity']['case_name'],
                      'aliases':sorted({name for row in rows for name in row['identity']['aliases']}),
                      'source_ids':[row['source_id'] for row in rows],
                      'identity_anchors':[a for row in rows for a in row['identity']['anchors']]})
    result={'contract':CONTRACT,'research_packet_sha256':packet_sha,'job_id':packet['job_id'],
            'resolver_sha256':file_sha(__file__),'reviewed_registry_sha256':hashlib.sha256(registry_raw).hexdigest(),
            'cases':cases,'sources':records,'resolved_case_count':len(cases),
            'status':'ready_for_original_case_selection' if len(cases)>=MIN_CASES else 'more_distinct_analog_cases_needed',
            'case_identity_scope':'Named facility identity only; no independent existence, measurement, or visual-coverage certification',
            'continuation':'Preserve cached pages. Use remaining research budget for additional named facilities; unresolved identities do not count. No network or model retry is triggered by this index.'}
    fresh,fresh_sha,_,fresh_sources=load_research(job_dir)
    if fresh_sha!=packet_sha or fresh!=packet or {s:row['text'] for s,row in sources.items()}!={s:row['text'] for s,row in fresh_sources.items()}:
        raise ValueError('Research changed while resolving analog case identities')
    result['index_sha256']=digest(result)
    return result


def require_three_cases(index):
    if index['resolved_case_count']<MIN_CASES:
        unknown=sum(row['state']=='unresolved' for row in index['sources'])
        raise CaseEvidenceRequired('Need three distinct resolved analog facilities; found '+str(index['resolved_case_count'])+
                                   ' ('+str(unknown)+' source identities unresolved). Cached research is preserved; obtain additional named cases within the remaining research budget.')


def prepare_case_index(job_dir):
    """Append an immutable sidecar; do not alter job, packet, sources or outputs."""
    job_dir=Path(job_dir).resolve();index=resolve_case_index(job_dir)
    folder=job_dir/'analog_case_indexes';folder.mkdir(exist_ok=True)
    if not folder.is_dir() or folder.is_symlink() or getattr(folder.lstat(),'st_file_attributes',0)&0x400:
        raise ValueError('Case index directory must be a plain local job directory')
    # Keep the on-disk name short for Windows paths; full hash and exact bytes
    # remain verified, including the unlikely prefix-collision case.
    path=folder/('cases-v1-'+index['index_sha256'][:20]+'.json');raw=canonical(index)
    if path.exists():
        if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('Preserved case index cannot be a link')
        if path.read_bytes()!=raw:raise ValueError('Preserved analog case index changed')
    else:
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=folder,prefix='.cases-',suffix='.partial',delete=False) as output:
                temporary=Path(output.name);output.write(raw);output.flush();os.fsync(output.fileno())
            try:os.link(temporary,path)
            except FileExistsError:
                if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400:
                    raise ValueError('Concurrent case index cannot be a link')
                if path.read_bytes()!=raw:raise ValueError('Concurrent case index publication changed bytes')
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'index_sha256':index['index_sha256'],'status':index['status'],'resolved_case_count':index['resolved_case_count']}


def validate_case_index(index,job_dir):
    if canonical(index)!=canonical(resolve_case_index(job_dir)):
        raise ValueError('Case index does not match exact current packet, source anchors and resolver')
