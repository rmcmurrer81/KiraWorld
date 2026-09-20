"""Deterministic, read-only topic selection. No models or source-file loading.

This module selects context, not truth or permission to publish. The caller
chooses the audience and preserves the selected subject and qualifications.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

_STOP = set('the and for that this with from about tell remember memories memory what when where how was were have had has you your yours my mine me our his her their they them then there just like want would could should please back left into says robert human synthetic source account story know again doing now recent currently are did does can'.split())
# Small explicit spelling/ordinary-word equivalences, not semantic inference.
_ALIASES = {'films':'film','movies':'film','movie':'film','cinema':'theater','theatre':'theater','theatres':'theater','theaters':'theater',
            'bicycles':'bicycle','bikes':'bicycle','bike':'bicycle','automobiles':'car','automobile':'car','cars':'car',
            'photographs':'photo','photograph':'photo','photos':'photo','pictures':'picture','recollections':'recollection'}

def topic_terms(text: str) -> set[str]:
    text=unicodedata.normalize('NFKC',str(text)).casefold()
    return {_ALIASES.get(word,word) for word in re.findall(r'[^\W\d_]+',text) if len(word)>=3 and word not in _STOP}

def public_request(text: str) -> bool:
    return bool(re.search(r'\b(?:publish|public|marketing|advertis\w*|press release|social media|post online)\b',str(text),re.I))

def _publication_approved(row: dict[str,Any]) -> bool:
    approval=row.get('publication_authorization')
    privacy=row.get('privacy')
    return (isinstance(privacy,dict) and privacy.get('level')=='owner_authorized_public'
            and isinstance(approval,dict) and all(approval.get(k)==v for k,v in
                {'status':'approved','granted_by':'owner','scope':'public_repository'}.items()))

def _strings(value: Any, maximum: int=16) -> list[str] | None:
    if not isinstance(value,list) or len(value)>maximum or any(not isinstance(x,str) or len(x)>1200 for x in value):return None
    return list(value)

def _live(row: dict[str,Any]) -> bool:
    return (row.get('active',True) is True and row.get('deleted',False) is False
            and not row.get('superseded_by'))

def _supersedes(row: dict[str,Any]) -> list[str] | None:
    value=row.get('supersedes',[])
    if isinstance(value,str):value=[value]
    if not isinstance(value,list) or len(value)>16 or any(not isinstance(x,str) or not x or len(x)>200 for x in value):return None
    return value

def select_person_context(rows: list[dict[str,Any]], *, subject: str, query: str,
                          scope: str='owner_visible', limit: int=5) -> list[dict[str,Any]]:
    """Select explicitly approved summaries, retaining subject/source/scopes.

    The legacy explicit-promotion route is accepted only for the exact owner,
    and never grants public scope. Missing approval does not become a fallback.
    Other-subject knowledge requires its own explicit publication permission.
    """
    if scope not in {'private','owner_visible','public'}:raise ValueError('Unknown memory audience scope')
    if not isinstance(subject,str) or not subject.strip():return []
    subject=subject.casefold();wanted=topic_terms(query)
    if not wanted or limit<=0:return []
    if public_request(query):scope='public'
    ids={};superseded=set();by_owner_id={};roots=[]
    for row in rows:
        if isinstance(row,dict):
            key=row.get('memory_id') or row.get('id')
            if isinstance(key,str):ids[key]=ids.get(key,0)+1
            owner=row.get('owner');source=row.get('source');links=_supersedes(row)
            if isinstance(owner,str) and isinstance(key,str):by_owner_id[(owner.casefold(),key)]=row
            # A later explicitly approved, live same-subject correction can
            # withdraw old context without disclosing its private replacement.
            # No date ordering, inferred links or cross-subject overwrite.
            if (row.get('status')=='approved' and _live(row) and isinstance(owner,str)
                    and isinstance(key,str) and key and isinstance(source,dict)
                    and isinstance(source.get('type'),str) and source['type'] and links is not None
                    and row.get('subject_id',owner)==owner):
                roots.extend((owner.casefold(),old) for old in links)
    # Follow only explicit same-subject approved/superseded history. This keeps
    # an older fact from resurfacing when its correction is corrected again.
    pending=list(roots)
    while pending:
        identity=pending.pop()
        if identity in superseded:continue
        superseded.add(identity)
        ancestor=by_owner_id.get(identity);owner,key=identity
        if not ancestor or ids.get(key)!=1 or ancestor.get('status') not in {'approved','superseded'}:continue
        source=ancestor.get('source');links=_supersedes(ancestor)
        if not isinstance(source,dict) or not source.get('type') or links is None:continue
        if ancestor.get('subject_id',ancestor.get('owner'))!=ancestor.get('owner'):continue
        pending.extend((owner,older) for older in links)
    ranked=[]
    for index,row in enumerate(rows):
        if not isinstance(row,dict):continue
        owner=row.get('owner');key=row.get('memory_id') or row.get('id')
        if not isinstance(owner,str) or not isinstance(key,str) or not key or len(key)>200 or ids[key]!=1:continue
        if not _live(row) or (owner.casefold(),key) in superseded or _supersedes(row) is None:continue
        if row.get('subject_id',owner)!=owner:continue
        own=owner.casefold()==subject
        tags=row.get('tags',[]);privacy=row.get('privacy');status=row.get('status')
        legacy=(status is None and own and row.get('source')=='conversation' and isinstance(tags,list)
                and 'explicitly_promoted' in tags)
        approved=status=='approved'
        public=approved and _publication_approved(row)
        if not (approved or legacy) or (not own and not public):continue
        sharing=privacy.get('sharing_rule') if isinstance(privacy,dict) else None
        if scope=='public' and not public:continue
        if scope=='owner_visible' and not (public or (own and sharing=='shareable_summary_only')
                or (legacy and row.get('private') is False)):continue
        if scope=='private' and not (own or public):continue
        summary=row.get('summary')
        if not isinstance(summary,str) or not summary.strip() or len(summary)>3000:continue
        source=row.get('source')
        if legacy:source={'type':'explicitly_promoted_conversation'}
        if not isinstance(source,dict) or not isinstance(source.get('type'),str) or not source['type']:continue
        # Source paths remain labels; never pull arbitrary source metadata or
        # private raw narratives into a summary-only context.
        source={key:source[key] for key in ('type','path','confidence','candidate_id') if key in source}
        if any(not isinstance(v,(str,int,float)) or isinstance(v,bool) for v in source.values()):continue
        if len(json.dumps(source,ensure_ascii=False))>2500:continue
        unknowns=_strings(row.get('known_unknowns',[]));guards=_strings(row.get('forbidden_inferences',[]))
        uncertainties=_strings(row.get('uncertainties',[]));event_date=row.get('event_date')
        if unknowns is None or guards is None or uncertainties is None:continue
        if event_date is not None and (not isinstance(event_date,str) or len(event_date)>200):continue
        aliases=_strings(row.get('recall_aliases',[]))
        if aliases is None:continue
        # Only approved shareable summaries/aliases are searchable here. Private
        # raw detail does not cause a public or owner-visible match.
        terms=topic_terms(summary+' '+' '.join(aliases))
        matches=wanted & terms
        if not matches:continue
        record={'record_id':key,'subject':owner,'viewpoint':'own_approved_record' if own else 'attributed_other_subject',
                'summary':summary,'source':source,'memory_type':row.get('memory_type'),
                'known_unknowns':unknowns,'uncertainties':uncertainties,'event_date':event_date,'forbidden_inferences':guards,
                'audience_scope':scope,'sharing_rule':sharing or 'explicit_owner_promotion',
                'record_timestamp':row.get('timestamp') or row.get('created_at') or None,
                'approval':'approved' if approved else 'explicitly_promoted_conversation'}
        if public:record['publication_authorization']={k:row['publication_authorization'][k] for k in ('status','granted_by','scope')}
        rendered=json.dumps(record,ensure_ascii=False)
        if len(rendered)>9000:continue  # Keep full qualifications or omit the record.
        mapped={'memory_id':key,'owner':owner,'summary':summary,'detail':'','timestamp':record['record_timestamp'],
                'importance':row.get('importance') if isinstance(row.get('importance'),dict) else {},'_recall_context':record}
        ranked.append((len(matches),index,mapped))
    ranked.sort(key=lambda item:(-item[0],item[1]))
    result=[];remaining=16000
    for _,_,record in ranked:
        size=len(json.dumps(record['_recall_context'],ensure_ascii=False))
        if size>remaining:continue
        result.append(record);remaining-=size
        if len(result)>=min(limit,8):break
    return result
