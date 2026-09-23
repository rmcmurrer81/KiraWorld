def presentation_setting(brief, packet, packet_sha256):
    """Derive a presentation location from the hash-bound original brief only."""
    result = {'contract':'bound_original_exterior_presentation_v1','setting':'unspecified',
              'reason':'verified_original_brief_unavailable','source':None}
    if brief is None:
        return result
    require(isinstance(brief,dict) and isinstance(packet,dict), 'Malformed presentation brief binding')
    # Saved research briefs use the original indented canonical format, not the
    # compact geometry canonicalization. Keep the existing identity exact.
    digest = sha((json.dumps(brief,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    require(digest == packet.get('brief_sha256') and packet.get('job_id') == 'world_research_'+digest[:20],
            'Presentation brief differs from the bound research packet')
    prompt = brief.get('prompt')
    require(isinstance(prompt,str) and len(prompt)<=20000, 'Invalid original presentation request')
    result['source'] = {'job_id':packet['job_id'],'brief_sha256':digest,
                        'request_sha256':sha(prompt.encode('utf-8')),'research_packet_sha256':packet_sha256}
    result['reason'] = 'no_explicit_supported_surface_setting'
    if brief.get('research_mode') != 'analog_to_original' or packet.get('research_mode') != 'analog_to_original':
        return result
    # Quoted source text is data. Unknown/conflicting/orbital settings get no
    # invented exterior; this intentionally bounded grammar is not an LLM guess.
    clean = re.sub(r'"[^"\n]*"|“[^”\n]*”|(?<!\w)\'[^\'\n]*\'(?!\w)', ' ', prompt).strip().lower()
    conflict = re.search(r'\b(?:orbit(?:al|ing)?|spacecraft|spaceship|space\s+station|lunar|moon|earth)\b',clean)
    denied = re.search(r"\b(?:don't|do not|not|no|without)\b[^.!?]*\b(?:mars|ground|terrain|surface|exterior)\b",clean)
    direct = re.match(r'^(?:please\s+)?(?:build|create|make|design)\s+(?:(?:an?|original|photorealistic|realistic|science-fiction|sci-fi|new)\s+){1,8}(?:mars(?:\s+surface)?\s+(?:base|habitat)|(?:base|habitat)\s+on\s+mars)\b',clean)
    if direct and not conflict and not denied:
        result.update(setting='mars_surface',reason='explicit_original_mars_base_request')
    return result


def capture_presentation_brief(research_packet_path):
    if research_packet_path is None:
        return None
    folder=Path(research_packet_path).absolute().parent;path=folder/'job.json'
    if not path.exists():
        return None
    packet=load_json(read_exact(research_packet_path));job=load_json(read_exact(path))
    require(job.get('job_kind')=='isolated_world_research_job' and job.get('schema_version')==1 and
            job.get('job_id')==folder.name==packet.get('job_id') and job.get('brief_sha256')==packet.get('brief_sha256'),
            'Presentation source is not the selected saved research job')
    brief=job.get('brief');require(isinstance(brief,dict), 'Saved presentation brief missing')
    presentation_setting(brief,packet,sha(read_exact(research_packet_path)))
    return brief


def verify_presentation(manifest):
    has_presentation='presentation_setting' in manifest or 'presentation_source_brief' in manifest
    if not has_presentation:
        require(manifest['inputs']['backend']['sha256'] != binding(__file__)['sha256'], 'New preview is missing its presentation binding')
        return presentation_setting(None,None,None)
    require('presentation_setting' in manifest and 'presentation_source_brief' in manifest, 'Incomplete presentation binding')
    row=manifest['inputs'].get('research_packet')
    packet=load_json(verify_binding(row)) if row else None
    expected=presentation_setting(manifest['presentation_source_brief'],packet,row['sha256'] if row else None)
    require(manifest['presentation_setting']==expected, 'Presentation setting differs from its exact source brief')
    return expected


