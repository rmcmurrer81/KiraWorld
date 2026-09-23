"""Refresh only presentation on explicit Open current preview; no model/research work.

Pipeline states and historical preview files remain untouched. The immutable
preview builder reuses a matching build or creates a separately pinned revision.
"""
from pathlib import Path
from world_saved_research import read_saved_research
from .pipeline import latest_preview
from .world_layout_preview import create_preview, verify_preview

PROJECT = Path(__file__).resolve().parents[2]


def refresh_saved_preview(job_dir):
    job = read_saved_research(Path(job_dir), job_root=PROJECT/'Data/world_research_jobs')
    previous = latest_preview(job['job_dir'])
    frozen = verify_preview(previous['manifest_path'], previous['manifest_sha256'])
    if frozen['source_mode'] != 'source_bound_original_layout':
        raise ValueError('Only a verified original layout can refresh its presentation')
    inputs = frozen['inputs']
    if Path(inputs['research_packet']['path']).parent != job['job_dir']:
        raise ValueError('Saved layout belongs to a different research job')
    refreshed = create_preview(inputs['geometry_source']['path'],
                               inputs['research_packet']['path'], inputs['blueprint']['path'])
    current = verify_preview(refreshed['manifest_path'], refreshed['manifest_sha256'])
    for key, row in inputs.items():
        if key in ('geometry_source', 'research_packet', 'blueprint') or key.startswith('research_cache_'):
            if current['inputs'].get(key) != row:
                raise ValueError('Preview refresh changed a saved layout source')
    # Detect a concurrent job change without writing or repairing its pointer.
    if read_saved_research(job['job_dir'], job_root=PROJECT/'Data/world_research_jobs') != job:
        raise ValueError('Saved research changed during preview refresh')
    if latest_preview(job['job_dir']) != previous:
        raise ValueError('Saved layout selection changed during preview refresh')
    verify_preview(previous['manifest_path'], previous['manifest_sha256'])
    return {**refreshed, 'previous_manifest_path':previous['manifest_path'],
            'presentation_refreshed':refreshed['manifest_path'] != previous['manifest_path'],
            'research_regenerated':False, 'model_jobs':0, 'saved_layout_state_modified':False}
