"""Rank bounded saved research leads without network, model or owner mutation."""
from __future__ import annotations
import ipaddress
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_LEADS=240
MAX_SUPPLEMENT=2
DENY_SEGMENTS={'ticket','tickets','billet','billets','billetterie','booking','book','checkout','account','accounts',
               'login','signin','sign-in','connexion','boutique','cart','basket','donate','donation','newsletter',
               'privacy','cookies','legal','search','recherche'}
MEDIA_SUFFIXES=('.pdf','.png','.jpg','.jpeg','.webp','.gif','.svg','.mp4','.webm','.mp3','.wav','.zip','.glb','.gltf')
LANGUAGES={'en','fr','es','de','it','zh','ja','pt','ru','ko','ar'}


def text(value):
    value=unicodedata.normalize('NFKD',str(value)).encode('ascii','ignore').decode().casefold()
    return re.sub(r'[^a-z0-9]+',' ',value).strip()


def normalize_url(value):
    if not isinstance(value,str) or len(value)>4096 or re.search(r'[\x00-\x20\\]',value):return None
    try:
        p=urlsplit(value);host=(p.hostname or '').lower()
        if p.scheme not in {'http','https'} or not host or p.username or p.password or p.port not in (None,80,443):return None
        if host in {'localhost','localhost.localdomain'} or host.endswith(('.local','.localhost')):return None
        try:
            if not ipaddress.ip_address(host).is_global:return None
        except ValueError:
            if '.' not in host:return None
        host=host.encode('idna').decode()
        netloc=host if p.port in (None,443 if p.scheme=='https' else 80) else host+':'+str(p.port)
        query=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
               if not k.casefold().startswith('utm_') and k.casefold() not in {'fbclid','gclid','msclkid'}]
        return urlunsplit((p.scheme,netloc,p.path or '/',urlencode(query),'')).rstrip('/') if p.path not in ('','/') else urlunsplit((p.scheme,netloc,'/',urlencode(query),''))
    except (ValueError,UnicodeError):return None


def homepage_key(url):
    p=urlsplit(url);parts=[x for x in p.path.split('/') if x]
    if not parts or len(parts)==1 and parts[0].lower() in LANGUAGES:
        return p.hostname.removeprefix('www.')+'/'
    return url


def origin(url):
    p=urlsplit(url);return p.scheme+'://'+p.netloc


def score_lead(lead,seed_origins,request_terms=()):
    """Heuristics rank leads only; they cannot certify authority or architecture."""
    url=lead['url'];p=urlsplit(url);parts=[x.lower() for x in p.path.split('/') if x]
    anchor=text(lead.get('text',''));words=text(p.path+' '+lead.get('text',''))
    language=parts[0] if parts and parts[0] in LANGUAGES else None
    body=parts[1:] if language else parts
    retail_request=bool(set(request_terms)&{'mall','malls','retail','shopping','shop','shops','store','stores'})
    store_path=bool((set(parts)|set(p.hostname.split('.')))&{'shop','shops','store','stores'})
    retail_directory=retail_request and (store_path or bool(re.search(
        r'\b(?:store|shop|retailer|tenant)s? (?:directory|directories|locations?)\b',words)))
    reasons=[];category='general';score=0;fetchable=True
    if lead.get('kind') in {'photo','video','document'} or p.path.lower().endswith(MEDIA_SUFFIXES):
        return {'score':-1000,'category':'uninspected_media_lead','fetchable':False,'reasons':['Media/document lead retained without downloading or visual inspection']}
    if (set(parts)&DENY_SEGMENTS or set(p.hostname.split('.'))&DENY_SEGMENTS or
        re.search(r'\b(?:buy|book|purchase)\s+(?:a\s+)?tickets?\b|\bsupport the\b',anchor)):
        return {'score':-900,'category':'transaction_or_account','fetchable':False,'reasons':['Ticket, account, shop or administrative destination has no architectural priority']}
    if (store_path and not retail_directory or re.search(
        r'\b(?:buy now|add to (?:cart|basket)|shop online|online (?:shop|store)|shopping cart|checkout)\b',words)
        or store_path and bool(set(parts)&{'product','products','buy','purchase'})):
        return {'score':-800,'category':'transaction_or_account','fetchable':False,
                'reasons':['Commerce destination, or shop/store lead outside a requested retail layout']}
    if not body:
        category='homepage';score=8;reasons.append('One homepage may discover relevant interior links')
    elif re.search(r'\b(?:floor plan|floor plans|ground plan|museum map|museum maps|map|maps|plan du musee|plan des salles|plan du palais|carte du)\b',words):
        category='maps_plans';score=100;reasons.append('Map or floor-plan wording in the exact discovered URL/anchor')
    elif retail_directory:
        category='retail_directory';score=70;reasons.append('Physical store directory or occupant lead for the requested retail layout')
    elif re.search(r'^(?:the-)?(?:palace|palais|architecture|building|architectural-history|museum-building)$',body[-1]):
        category='architecture_overview';score=90;reasons.append('Architectural overview or palace index')
    elif re.search(r'\b(?:architecture|architectural|palace|palais|gallery|galerie|pavilion|pavillon|courtyard|pyramid|pyramide|staircase|escalier|fortress|construction)\b',words):
        category='architecture_detail';score=75;reasons.append('Architectural or room-specific content')
    elif re.search(r'\b(?:habitats?|facilit(?:y|ies)|analogs?|analogues?|modules?|laborator(?:y|ies)|quarters|living spaces?|isolation)\b',words):
        category='facility_layout';score=70;reasons.append('Habitat, analog facility or functional-space material')
    elif re.search(r'\b(?:entrance|entrances|directions|accessibility|entree|entrees|acces|access)\b',words):
        category='entrances_access';score=65;reasons.append('Entrance or access information')
    elif re.search(r'\b(?:visitor trails|room|rooms|galleries|salles|floor|floors)\b',words):
        category='room_connections';score=45;reasons.append('Room and visitor-route lead')
    elif re.search(r'\b(?:garden|gardens|jardin|jardins|history|histoire)\b',words):
        category='context';score=30;reasons.append('Physical-site context')
    elif re.search(r'\b(?:exhibition|exhibitions|event|events|concert|concerts|hours|admission|faq|restaurant|cafe)\b',words):
        score=-20;reasons.append('Visitor operations or event content is lower priority')
    elif set(words.split()) & set(request_terms):
        category='request_related';score=35;reasons.append('Discovered lead wording overlaps the requested place or world')
    if origin(url) in seed_origins:
        score+=15;reasons.append('Same origin as a retrieved seed; not independent authority approval')
    if language=='en':score+=8;reasons.append('English version matches this English-language research request')
    elif language:score-=3
    if 'wikipedia.org' in p.hostname:score-=12;reasons.append('General encyclopedia lead loses to physical-site material')
    if re.search(r'\b(?:available|open|closed) (?:rooms|galleries)\b|list of available',words):
        score-=35;reasons.append('Current opening availability is not a floor-plan or spatial measurement')
    return {'score':score,'category':category,'fetchable':fetchable,'reasons':reasons}


def rank_candidates(job,extra_sources=()):
    retrieved=[s for s in [*job.get('sources',[]),*extra_sources] if s.get('state')=='retrieved_text']
    seed_origins={origin(u) for s in retrieved if (u:=normalize_url(s.get('final_url') or s.get('requested_url')))}
    # Reserve bounded intake for explicitly supplied URLs before page links can
    # fill MAX_LEADS. Their later score bonus is ineffective if truncated first.
    leads=[{'url':url,'text':'','kind':'link','evidence':{'kind':'explicit_user_url','source_url_index':index}}
           for index,url in enumerate(job.get('brief',{}).get('source_urls',[])[:8])]
    request_terms=set(text(job.get('brief',{}).get('prompt','')+' '+job.get('brief',{}).get('subject','')).split())
    request_terms={word for word in request_terms if len(word)>=4} - {'build','create','original','world','please','make','style'}
    for source in retrieved:
        for i,item in enumerate(source.get('discovered_links',[])[:80]):
            leads.append({**item,'evidence':{'kind':'retrieved_page_link','source_id':source.get('source_id'),
                'source_url':source.get('final_url') or source.get('requested_url'),
                'content_sha256':(source.get('content_binding') or {}).get('sha256'),
                'text_sha256':(source.get('text_binding') or {}).get('sha256'),'link_index':i}})
    for task in job.get('tasks',[])[:8]:
        for item in (task.get('result') or {}).get('results',[])[:4]:
            leads.append({'url':item.get('url'),'text':item.get('title',''),'kind':'link',
                'evidence':{'kind':'search_lead','task_id':task.get('id'),'response_sha256':(task.get('result') or {}).get('response_sha256')}})
    known={homepage_key(u) for source in [*job.get('sources',[]),*extra_sources]
           if (u:=normalize_url(source.get('requested_url')))}
    known.update(homepage_key(u) for source in retrieved if (u:=normalize_url(source.get('final_url'))))
    unique={};rejected=[]
    for lead in leads[:MAX_LEADS]:
        url=normalize_url(lead.get('url'))
        if not url:
            rejected.append({'url':lead.get('url'),'reason':'Invalid/nonpublic URL shape'});continue
        lead={**lead,'url':url};scored={**lead,**score_lead(lead,seed_origins,request_terms)}
        if lead['evidence']['kind']=='explicit_user_url' and scored['fetchable']:
            scored['score']+=200;scored['reasons'].append('Explicit user source URL retained ahead of automatically discovered leads')
        key=homepage_key(url)
        if key in known:
            scored.update(fetchable=False,category='already_attempted_or_homepage_duplicate')
            scored['reasons'].append('Already attempted/cached, including language-only homepage duplicates; no automatic refetch')
        previous=unique.get(key)
        if previous is None or (scored['score'],scored['evidence']['kind']=='retrieved_page_link')>(previous['score'],previous['evidence']['kind']=='retrieved_page_link'):
            unique[key]=scored
    # Preserve the supplied order of explicit sources, including across resumes;
    # relevance scores apply to automatically discovered leads after them.
    ranked=sorted(unique.values(),key=lambda r:(
        0 if r['evidence']['kind']=='explicit_user_url' else 1,
        r['evidence']['source_url_index'] if r['evidence']['kind']=='explicit_user_url' else -r['score'],r['url']))
    return {'ranked':ranked,'rejected':rejected,'lead_limit':MAX_LEADS,'network_queries':0,
            'authority_status':'same_origin_preference_only','inspection_status':'ranked_leads_not_verified_facts'}


def select_candidates(job,*,max_new_pages=None,supplemental=False,extra_sources=()):
    used=len(job.get('sources',[]));budget=job['brief']['budgets']['max_pages']
    remaining=max(0,budget-used)
    if max_new_pages is None:max_new_pages=remaining
    if type(max_new_pages) is not int or max_new_pages<0 or max_new_pages>(MAX_SUPPLEMENT if supplemental else 8):
        raise ValueError('Invalid new-page budget')
    allowance=max_new_pages if supplemental else min(max_new_pages,remaining)
    ranked=rank_candidates(job,extra_sources)
    eligible=[r for r in ranked['ranked'] if r['fetchable'] and r['score']>=25]
    if not eligible:
        # A new job must be able to retrieve one discovery seed before any
        # architectural links exist; do not spend the whole budget on seeds.
        eligible=[r for r in ranked['ranked'] if r['fetchable'] and r['category']=='homepage'][:1]
    if not eligible:
        # Search can return useful content pages without recognized architecture
        # vocabulary. Admit one bounded discovery page, never a denied/media or
        # explicitly low-priority event lead; the collector re-ranks its links.
        eligible=[r for r in ranked['ranked'] if r['fetchable'] and r['category']=='general' and r['score']>=0][:1]
    selected=[];categories=set()
    # Avoid spending both slots on language variations of the same map category.
    for distinct in (True,False):
        for row in eligible:
            if len(selected)>=allowance:break
            if row in selected or (distinct and row['category'] in categories
                                   and row['evidence']['kind']!='explicit_user_url'):continue
            selected.append(row);categories.add(row['category'])
    return {**ranked,'selected':selected,'original_page_budget':budget,'original_chosen_sources':used,
            'original_remaining_pages':remaining,'supplemental_allowance':max_new_pages if supplemental else 0,
            'new_page_allowance':allowance,'queries_added':0,'resident_job_mutated':False}
