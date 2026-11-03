#!/usr/bin/env python3
"""Preview or install optional native client roles from this installed skill."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import stat
import sys
import uuid


ROLES = (
    'chief_of_staff', 'project_manager', 'implementation_worker',
    'architecture_advisor', 'code_advisor', 'visual_advisor',
)


class InstallError(Exception):
    pass


def asset_paths(client):
    if client == 'codex':
        return [*(f'agents/{name}.toml' for name in ROLES),
                'chief-of-staff.config.toml', 'chief-of-staff']
    return [*(f'agents/{name.replace("_", "-")}.md' for name in ROLES),
            'chief-of-staff.settings.json']


def check_parents(path, root):
    """Reject symlinks and non-directory conflicts below the chosen home/root."""
    path.relative_to(root)
    for parent in reversed([path.parent, *path.parent.parents]):
        if parent != root and root not in parent.parents:
            continue
        if parent.is_symlink():
            raise InstallError(f'Symlink parent is not allowed: {parent}')
        if parent.exists() and not parent.is_dir():
            raise InstallError(f'Parent is not a directory: {parent}')


@contextmanager
def parent_fd(home, relative):
    """Use no-follow directory handles so replacements cannot redirect writes."""
    fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            try:
                os.mkdir(part, mode=0o755, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def same_file(path, content, executable):
    if path.is_symlink() or not path.is_file():
        return False
    mode = path.stat().st_mode
    return path.read_bytes() == content and (not executable or bool(mode & stat.S_IXUSR))


def write_asset(home, relative, content, executable):
    destination = home / relative
    check_parents(destination, home)
    with parent_fd(home, relative) as fd:
        try:
            current = os.stat(relative.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current and not (stat.S_ISREG(current.st_mode) or stat.S_ISLNK(current.st_mode)):
            raise InstallError(f'Destination is not a regular file or symlink: {destination}')
        # Keep restrictive existing permissions; a launcher additionally needs owner execute.
        mode = stat.S_IMODE(current.st_mode) if current and stat.S_ISREG(current.st_mode) else (0o755 if executable else 0o644)
        if executable:
            mode |= stat.S_IXUSR
        token = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex
        temporary = f'.{relative.name}.shipyard-{token}.tmp'
        backup = None
        try:
            output = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=fd)
            with os.fdopen(output, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fchmod(stream.fileno(), mode)
            if current:
                backup = f'{relative.name}.shipyard-backup-{token}'
                os.rename(relative.name, backup, src_dir_fd=fd, dst_dir_fd=fd)
            os.rename(temporary, relative.name, src_dir_fd=fd, dst_dir_fd=fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass
        return f'Installed global asset: {destination}' + (f' (backup: {destination.parent / backup})' if backup else '')


def install(skill_root, home, client='both', apply=False):
    """Validate every selected source and target before previewing or writing."""
    if client not in ('codex', 'claude', 'both'):
        raise InstallError(f'Unknown client: {client}')
    root = Path(skill_root).resolve()
    home = Path(os.path.abspath(Path(home).expanduser()))
    selected = ('codex', 'claude') if client == 'both' else (client,)
    plan = []
    for chosen in selected:
        marker = home / ('.agents' if chosen == 'codex' else '.claude') / 'skills/shipyard/SKILL.md'
        if not marker.is_file():
            raise InstallError(f'Install shipyard globally for {chosen} first; missing installed skill: {marker}')
        for asset in asset_paths(chosen):
            source = root / 'assets' / chosen / asset
            check_parents(source, root)
            if source.is_symlink() or not source.is_file():
                raise InstallError(f'Missing regular package asset: {source}')
            relative = Path(f'.{chosen}') / asset
            destination = home / relative
            check_parents(destination, home)
            if (destination.exists() or destination.is_symlink()) and not (destination.is_symlink() or destination.is_file()):
                raise InstallError(f'Destination is not a regular file or symlink: {destination}')
            content = source.read_bytes()
            executable = chosen == 'codex' and asset == 'chief-of-staff'
            unchanged = same_file(destination, content, executable)
            plan.append((relative, content, executable, unchanged))
    messages = ['Global scope: optional native agent roles and launchers only; global instructions and settings are unchanged.']
    for relative, content, executable, unchanged in plan:
        if unchanged:
            messages.append(f'Unchanged global asset: {home / relative}')
        elif apply:
            messages.append(write_asset(home, relative, content, executable))
        else:
            messages.append(f'Would install global asset: {home / relative}')
    return messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', choices=('codex', 'claude', 'both'), default='both')
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--apply', action='store_true', help='Write selected assets; default only previews')
    args = parser.parse_args()
    try:
        print('\n'.join(install(Path(__file__).resolve().parents[1], **vars(args))))
    except (InstallError, OSError, ValueError) as exc:
        print(f'Setup skipped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
