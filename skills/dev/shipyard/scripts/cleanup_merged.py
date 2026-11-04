#!/usr/bin/env python3
"""Delete one released, merged PR branch after checking GitHub and live Git refs."""

import argparse
import json
import re
import subprocess
import sys
from urllib.parse import quote, urlparse


class CleanupError(Exception):
    pass


def run(argv):
    result = subprocess.run(argv, text=True, capture_output=True)
    if result.returncode:
        raise CleanupError(f"{' '.join(argv[:3])}: {result.stderr.strip()}")
    return result.stdout.strip()


def github_repo(url):
    if url.startswith('git@github.com:'):
        path = url[len('git@github.com:'):]
    else:
        parsed = urlparse(url)
        if parsed.scheme not in ('https', 'ssh') or parsed.hostname != 'github.com':
            raise CleanupError('Remote must be a GitHub HTTPS or SSH URL')
        path = parsed.path.lstrip('/')
    if path.endswith('.git'):
        path = path[:-4]
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path):
        raise CleanupError('Invalid GitHub repository URL')
    return path.casefold()


def cleanup(repo, pr, remote='origin', apply=False, released=False, execute=run):
    """Validate provenance, then use per-ref compare-and-delete operations."""
    if not released:
        raise CleanupError('--released is required: coordinator must release all task/session claims')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise CleanupError('--repo must be owner/name')
    if not isinstance(pr, int) or pr < 1 or remote.startswith('-'):
        raise CleanupError('Invalid PR number or remote name')
    expected_repo = repo.casefold()
    # Check both URLs: a pushurl can point elsewhere even when fetch uses origin.
    for mode in ([], ['--push']):
        urls = execute(['git', 'remote', 'get-url', *mode, '--all', remote]).splitlines()
        if len(urls) != 1 or github_repo(urls[0]) != expected_repo:
            raise CleanupError('Fetch/push remote must uniquely match --repo')
    def api(endpoint):
        return json.loads(execute(['gh', 'api', '--hostname', 'github.com', endpoint]))

    metadata = api(f'repos/{repo}')
    pull = api(f'repos/{repo}/pulls/{pr}')
    if not pull.get('merged_at') or pull.get('merged') is not True:
        raise CleanupError('PR is not confirmed merged')
    head, base = pull['head'], pull['base']
    for side in (head, base):
        if (side.get('repo') or {}).get('full_name', '').casefold() != expected_repo:
            raise CleanupError('Only same-repository PR branches can be cleaned')
    branch, sha = head['ref'], head['sha']
    protected = {
        metadata['default_branch'], base['ref'], 'main', 'master', 'develop',
        'development', 'trunk', 'release', 'stable', 'staging', 'production', 'prod',
    }
    if branch in protected or branch.startswith(('release/', 'releases/')):
        raise CleanupError(f'Protected branch: {branch}')
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
        raise CleanupError('Invalid PR head SHA')
    ref = f'refs/heads/{branch}'
    execute(['git', 'check-ref-format', ref])
    def check_worktrees():
        worktrees = execute(['git', 'worktree', 'list', '--porcelain']).splitlines()
        if f'branch {ref}' in worktrees:
            raise CleanupError(f'Branch is checked out in a worktree: {branch}')

    def local_head():
        rows = [
            line.split() for line in execute(
                ['git', 'for-each-ref', '--format=%(refname) %(objectname) %(symref)', ref]
            ).splitlines() if line.split()[0] == ref
        ]
        if any(len(row) != 2 for row in rows):
            raise CleanupError('Local branch is a symbolic ref; preserve its target')
        if len(rows) > 1 or (rows and rows[0][1] != sha):
            raise CleanupError('Local branch has changed since the merged PR')
        return bool(rows)

    check_worktrees()
    local = local_head()
    remote_rows = execute(['git', 'ls-remote', '--heads', remote, ref]).splitlines()
    if len(remote_rows) > 1:
        raise CleanupError('Ambiguous remote branch')
    if remote_rows and remote_rows[0].split() != [sha, ref]:
        raise CleanupError('Remote branch has changed since the merged PR')
    if remote_rows:
        protection = api(f'repos/{repo}/branches/{quote(branch, safe="")}')
        if not isinstance(protection, dict) or protection.get('protected') is not False:
            raise CleanupError('Remote branch is protected or its protection is unknown')
    if not local and not remote_rows:
        return f'Already absent: {branch}'
    if not apply:
        targets = '/'.join(name for name, exists in [('local', local), ('remote', remote_rows)] if exists)
        return f'Dry run: delete {targets} {branch} at {sha}'
    # Delete remote first: a failed lease must preserve the local recovery ref.
    if remote_rows:
        local_head()
        check_worktrees()
        execute(['git', 'push', f'--force-with-lease={ref}:{sha}', remote, f':{ref}'])
    if local:
        try:
            local_head()
            check_worktrees()
            # Never dereference an alias introduced after the checks.
            execute(['git', 'update-ref', '--no-deref', '-d', ref, sha])
        except CleanupError as exc:
            if remote_rows:
                raise CleanupError(f'Remote branch deleted; local cleanup skipped: {exc}') from exc
            raise
    return f'Deleted: {branch} at {sha}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, help='GitHub owner/name matching the Git remote')
    parser.add_argument('--pr', required=True, type=int)
    parser.add_argument('--remote', default='origin')
    parser.add_argument('--released', action='store_true', help='Coordinator confirms no live task/session claims this branch')
    parser.add_argument('--apply', action='store_true', help='Perform deletion; default is a read-only dry run')
    args = parser.parse_args()
    try:
        print(cleanup(**vars(args)))
    except (CleanupError, KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        print(f'Skipped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
