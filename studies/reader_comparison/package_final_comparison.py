"""Archive the frozen six-endpoint analysis dependency closure without secrets or weights."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    out = args.out.resolve()
    if out.exists():
        raise ValueError('Preserve existing package')
    queue, files = [], {}

    def add(path, expected=None):
        p = Path(path)
        p = (root/p).resolve() if not p.is_absolute() else p.resolve()
        relative = p.relative_to(root)
        if any(part in ['private', '.git'] or part.startswith('.env') for part in relative.parts):
            raise ValueError('Forbidden dependency path')
        if p.suffix in ['.safetensors', '.bin', '.pt', '.pth']:
            raise ValueError('Model/activation weight dump outside analysis scope')
        sha = digest(p)
        if expected is not None and sha != expected:
            raise ValueError('Changed dependency: '+str(relative))
        if str(relative) not in files:
            files[str(relative)] = {'sha256': sha, 'bytes': p.stat().st_size}
            queue.append(p)

    run = Path('runs/reader-comparison')
    for endpoint in ['before_action', 'end_prompt']:
        for name in ['summary.json', 'cases.json', 'evaluation.log']:
            add(run/('accepted-evaluation-'+endpoint)/name)
        for name in ['casebook.json', 'casebook.md', 'complete.json']:
            add(run/('accepted-casebook-'+endpoint)/name)
        add(run/('accepted-calibration-'+endpoint)/'lock.json')
        cases = json.loads((run/('accepted-evaluation-'+endpoint)/'cases.json').read_text())
        for row in cases:
            for name in ['cells.json', 'complete.json']:
                add(run/'production-captures'/row['episode_id']/name)
    for endpoint in ['during_action', 'after_action', 'before_action_32', 'before_action_64']:
        prefix = 'standard' if endpoint in ['during_action', 'after_action'] else 'accepted'
        for name in ['summary.json', 'cases.json']:
            add(run/(prefix+'-evaluation-'+endpoint)/name)
        add(run/(prefix+'-calibration-'+endpoint)/'lock.json')
        add(run/(prefix+'-test-'+endpoint)/'interpretations'/'manifest.json')
        add(run/(prefix+'-test-'+endpoint)/'interpretations'/'scores.json')
    for name in ['four-endpoint-heldout-reviews/complete.json', 'four-endpoint-evaluation-handoff/complete.json']:
        add(run/name)
    for name in ['four-endpoint-measured-results.json', 'four-endpoint-evaluation-handoff-plan.json', 'four-endpoint-heldout-review-plan-v2.json', 'technical-record-docx-qa-final.json']:
        add(Path('studies/reader_comparison/evidence')/name)
    add(Path('reports/reader-comparison/four-endpoint-heldout-results.md'))
    for name in ['production-audits/audits.json', 'production-policy-reviews/policy-reviews.json',
                 'production-policy-reviews/complete.json', 'production-captures/manifest.json',
                 'accepted-primary-test-reviews-final26/complete.json']:
        add(run/name)
    for name in ['accepted-primary-heldout-results.md', 'accepted-primary-casebook-audit.md',
                 'temporal-readout-visibility.md', 'technical-record.md', 'technical-record.docx']:
        add(Path('reports/reader-comparison')/name)
    for name in ['legacy-specificity-review-audit.json', 'legacy-specificity-summary-receipt-audit.json', 'oracle-temporal-fidelity-audit.json', 'legacy-remaining-exact-cache-inventory.json']:
        add(Path('studies/reader_comparison/evidence')/name)
    for panel in ['specificity-controls', 'monitor-controls']:
        for name in ['summary.json', 'cases.json']:
            add(Path('reports')/('jsummary-'+panel)/name)
    for name in ['legacy-specificity-results.md', 'oracle-temporal-fidelity-audit.md']:
        add(Path('reports/reader-comparison')/name)
    for name in ['legacy-remaining-review-audit.json', 'legacy-remaining-summary-audit.json', 'remaining-closeout-verification.json']:
        add(Path('studies/reader_comparison/evidence')/name)
    for panel in ['template-challenge', 'fresh-completion']:
        for name in ['summary.json', 'cases.json']:
            add(Path('reports')/('jsummary-'+panel)/name)
    add(Path('reports/reader-comparison/legacy-remaining-results.md'))
    add(Path('reports/summarizer-extension-findings.md'))
    tracked = subprocess.check_output(['git', 'ls-files', 'studies/reader_comparison'], text=True).splitlines()
    for path in tracked:
        p = Path(path)
        if p.suffix == '.py' or p.parent == Path('studies/reader_comparison') and p.suffix in ['.json', '.md']:
            add(p)
    add(Path(__file__))

    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith('source_hashes') or key == 'label_sources':
                    if isinstance(child, dict):
                        for path, sha in child.items():
                            if isinstance(sha, str) and len(sha) == 64:
                                add(path, sha)
                else:
                    references(child)
        elif isinstance(value, list):
            for child in value:
                references(child)

    index = 0
    while index < len(queue):
        p = queue[index]
        index += 1
        if p.suffix == '.json':
            references(json.loads(p.read_text()))
    out.mkdir(parents=True)
    manifest = {'original_root': str(root), 'files': files, 'file_count': len(files),
                'uncompressed_bytes': sum(v['bytes'] for v in files.values()),
                'scope': 'Frozen six-endpoint and all registered legacy extension panels analysis evidence and declared source dependency closure. Excludes credentials, full weight files, full activation tensors and live budget ledger. Not a complete regeneration bundle. Original absolute paths in frozen manifests are preserved; running unchanged scripts expects the recorded root, or a separately validated relocation procedure. Known checksums permit independent inspection at other locations.'}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    archive = out/'final-comparison-evidence.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for relative, record in sorted(files.items()):
            path = root/relative
            if digest(path) != record['sha256']:
                raise ValueError('Input changed while packaging')
            info = tar.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mtime = 0
            with path.open('rb') as stream:
                tar.addfile(info, stream)
    # Verify the actual archive, not only the source files used to build it.
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if {m.name for m in members} != set(files) or len(members) != len(files):
            raise ValueError('Archive inventory differs')
        for member in members:
            h = hashlib.sha256()
            stream = tar.extractfile(member)
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
            if h.hexdigest() != files[member.name]['sha256']:
                raise ValueError('Archive payload differs')
    result = {'archive_sha256': digest(archive), 'archive_bytes': archive.stat().st_size,
              'manifest_sha256': digest(out/'manifest.json'), 'verified_members': len(files),
              'scope': manifest['scope']}
    (out/'verified.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
