"""Deduplicate unchanged, validation-only summary jobs for one model load."""
import argparse
from pathlib import Path
from collect_local_readers import load_jobs
from smoke import digest, write_json


def prepare(directories, out):
    if out.exists():
        raise ValueError('Preserve existing batch')
    unique, sources, counts = {}, {}, {}
    for directory in directories:
        manifest, jobs, _ = load_jobs(directory)
        if manifest['phase'] != 'validation' or manifest['stage'] != 'summaries':
            raise ValueError('Only validation summaries may enter this batch')
        for name in ['manifest.json', 'jobs.json', 'aliases.json']:
            path = directory/name
            sources[str(path.resolve())] = digest(path)
        counts[str(directory.resolve())] = len(jobs)
        for job in jobs:
            key = job['request_id']
            if key in unique and unique[key] != job:
                raise ValueError('Conflicting exact request payloads')
            unique[key] = job
    out.mkdir(parents=True)
    write_json(out/'jobs.json', {'jobs':[unique[key] for key in sorted(unique)]})
    write_json(out/'manifest.json', {
        'phase':'validation', 'stage':'summaries', 'unique_requests':len(unique),
        'source_jobs':counts, 'source_hashes':sources,
        'jobs_sha256':digest(out/'jobs.json'), 'code_sha256':digest(__file__),
        'scope':'Scheduling union only; original prepared aliases and collectors remain authoritative. Does not authorize inference before matching reader gates pass.'})
    return len(unique)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sources', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print({'unique_requests':prepare(a.sources, a.out)}, flush=True)


if __name__ == '__main__':
    main()
