#!/usr/bin/env python3
"""Resolve or explicitly persist Shipyard model defaults; never edit native clients."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
import runpy
from pathlib import Path
import stat
import subprocess
import sys
import uuid


TIERS = ('economy', 'balanced', 'deep')
_REGISTRY = runpy.run_path(str(Path(__file__).resolve().with_name('stage_registry.py')))
ROLES = _REGISTRY['ROLES']
STAGES = _REGISTRY['STAGES']
TARGETS = _REGISTRY['TARGETS']
FIELDS = {'tier', 'model', 'effort', 'max_tier', 'policy'}


class SettingsError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SettingsError(message)


def role_name(role):
    require(isinstance(role, str), 'Role must be a string')
    name = role.replace('_', '-')
    require(name in ROLES, f'Unknown role: {role}')
    return name


def stage_name(stage):
    require(stage is None or (isinstance(stage, str) and stage in STAGES), f'Unknown stage: {stage}')
    return stage


def pins(values, *, allow_policy=True):
    require(isinstance(values, dict), 'Settings pins must be an object')
    allowed = FIELDS if allow_policy else FIELDS - {'policy'}
    require(not set(values) - allowed, 'Unknown settings field or policy outside client defaults')
    for key, value in values.items():
        if value is None:
            continue
        if key == 'tier':
            require(value in (*TIERS, 'auto'), 'Invalid tier')
        elif key == 'max_tier':
            require(value in TIERS, 'Invalid max_tier')
        else:
            require(isinstance(value, str) and bool(value.strip()), f'{key} must be a nonempty string or null')
    return dict(values)


def normalize(values):
    """Normalize only newly set/task pins, retaining explicit null tombstones."""
    values = pins(values)
    if values.get('tier') is not None:
        values.setdefault('model', None)
        values.setdefault('effort', None)
    elif values.get('model') is not None:
        values.setdefault('tier', 'auto')
        values.setdefault('effort', None)
    return values


def validate(document):
    require(isinstance(document, dict) and not set(document) - {'version', 'clients'}, 'Invalid settings document keys')
    require(type(document.get('version')) is int and document['version'] == 1, 'Settings require version 1')
    clients = document.get('clients', {})
    require(isinstance(clients, dict) and not set(clients) - {'codex', 'claude'}, 'Unknown settings client')
    result = {'version': 1, 'clients': {}}
    for client, config in clients.items():
        require(isinstance(config, dict) and not set(config) - {'defaults', 'roles', 'stages'}, 'Invalid client settings keys')
        entry = {}
        if 'defaults' in config:
            entry['defaults'] = pins(config['defaults'])
        if 'roles' in config:
            require(isinstance(config['roles'], dict), 'Role settings must be an object')
            entry['roles'] = {}
            for role, value in config['roles'].items():
                name = role_name(role)
                require(name not in entry['roles'], 'Duplicate normalized role')
                entry['roles'][name] = pins(value, allow_policy=False)
        if 'stages' in config:
            require(isinstance(config['stages'], dict), 'Stage settings must be an object')
            entry['stages'] = {}
            for stage, roles in config['stages'].items():
                stage_name(stage)
                require(isinstance(roles, dict), 'Stage roles must be an object')
                entry['stages'][stage] = {}
                for role, value in roles.items():
                    name = role_name(role)
                    require(name not in entry['stages'][stage], 'Duplicate normalized stage role')
                    entry['stages'][stage][name] = pins(value, allow_policy=False)
        result['clients'][client] = entry
    return result


def absolute(path, cwd):
    return Path(os.path.abspath(cwd / Path(path).expanduser()))


def safe_path(path):
    for parent in reversed(path.parents):
        require(not parent.is_symlink(), f'Symlink parent is not allowed: {parent}')
        require(not parent.exists() or parent.is_dir(), f'Parent is not a directory: {parent}')
    require(not path.is_symlink(), f'Symlink settings/lock file is not allowed: {path}')
    require(not path.exists() or path.is_file(), f'Settings path is not a regular file: {path}')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def read_document(path, parent=None):
    if parent is None:
        safe_path(path)
    try:
        fd = os.open(path.name if parent is not None else path, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        return {'version': 1, 'clients': {}}, None
    with os.fdopen(fd, 'rb') as stream:
        require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), f'Settings path is not a regular file: {path}')
        raw = stream.read()
    return validate(json.loads(raw, object_pairs_hook=unique_object)), raw


def locations(project=None, user_config=None, no_project=False, trust_project=False, cwd=None):
    cwd = Path(os.path.abspath(cwd or Path.cwd()))
    if user_config is None:
        xdg = os.environ.get('XDG_CONFIG_HOME')
        require(not xdg or Path(xdg).is_absolute(), 'XDG_CONFIG_HOME must be absolute')
        user = (Path(xdg) if xdg else Path.home() / '.config') / 'shipyard/model-settings.json'
    else:
        user = absolute(user_config, cwd)
    project_path, warnings = None, []
    if not no_project:
        if project is not None:
            root = absolute(project, cwd)
            require(not root.exists() or root.is_dir(), 'Explicit project must be a directory')
        else:
            found = subprocess.run(['git', '-C', str(cwd), 'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=10)
            root = Path(found.stdout.strip()) if found.returncode == 0 else None
        if root is not None:
            candidate = root / '.shipyard/model-settings.json'
            if project is not None or trust_project:
                project_path = candidate
            elif candidate.exists() or candidate.is_symlink():
                warnings.append(f'Ignoring untrusted project settings: {candidate}; pass --project or --trust-project after authorization')
    return user, project_path, warnings, cwd


def policy_module():
    # Lazy loading keeps planner imports acyclic; this module never dispatches a model.
    spec = importlib.util.spec_from_file_location('shipyard_settings_policy', Path(__file__).with_name('model_policy.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assemble(client, role, user, project, documents, overrides, warnings, cwd, stage=None):
    layers = [{'name': 'builtin', 'path': None, 'values': {'tier': 'auto', 'max_tier': 'deep'}}]
    for scope, path in [('user', user), ('project', project)]:
        if path is None:
            continue
        entry = documents[path].get('clients', {}).get(client, {})
        entries = [('defaults', entry.get('defaults', {})),
                   (f'roles.{role}', entry.get('roles', {}).get(role, {}))]
        if stage is not None:
            entries.append((f'stages.{stage}.{role}', entry.get('stages', {}).get(stage, {}).get(role, {})))
        for suffix, values in entries:
            if values:
                layers.append({'name': f'{scope}.{suffix}', 'path': str(path), 'values': dict(values)})
    if overrides:
        explicit = normalize({k: str(v) if isinstance(v, Path) else v for k, v in overrides.items()})
        if explicit.get('policy') is not None:
            explicit['policy'] = str(absolute(explicit['policy'], cwd))
        layers.append({'name': 'task', 'path': None, 'values': explicit})
    values, sources, ceilings = {}, {}, []
    policy_path = None
    for layer in layers:
        for field, value in layer['values'].items():
            origin = {'layer': layer['name'], 'path': layer['path']}
            if field == 'max_tier':
                if value is not None:
                    ceilings.append({**origin, 'tier': value})
                continue
            sources[field] = {**origin, **({'cleared': True} if value is None else {})}
            if field == 'policy':
                policy_path = None if value is None else str(absolute(value, Path(layer['path']).parent if layer['path'] else cwd))
            elif value is None:
                values.pop(field, None)
            else:
                values[field] = value
    strictest = min(ceilings, key=lambda c: TIERS.index(c['tier']))
    values.setdefault('tier', 'auto')
    values['max_tier'] = strictest['tier']
    sources['max_tier'] = {key: strictest[key] for key in ('layer', 'path')}
    module = policy_module()
    chosen_policy = module.load_policy(policy_path)
    validation = module.select(chosen_policy, client, role=role, tier=values['tier'],
                               model=values.get('model'), effort=values.get('effort'), max_tier='deep', env={})
    # An auto budget may conflict with a future task's role/risk floor; the actual planner decides then.
    if values['tier'] != 'auto' or values.get('model') is not None:
        require(TIERS.index(validation['tier']) <= TIERS.index(values['max_tier']), 'Explicit selection exceeds the strictest saved/task max_tier')
    return {'values': values, 'policy_path': policy_path, 'sources': sources,
            'layers': layers, 'warnings': list(warnings), 'ceiling_sources': ceilings,
            'stage': stage, 'role': role}


def resolve(client, role='implementation-worker', *, project=None, user_config=None,
            overrides=None, no_project=False, trust_project=False, cwd=None, stage=None):
    stage = stage_name(stage)
    require(client in ('codex', 'claude'), 'Unknown client')
    role = role_name(role)
    user, project_path, warnings, cwd = locations(project, user_config, no_project, trust_project, cwd)
    documents = {path: read_document(path)[0] for path in (user, project_path) if path is not None}
    return assemble(client, role, user, project_path, documents, overrides, warnings, cwd, stage)


@contextmanager
def open_parent(path):
    """Create only the selected settings parent, using no-follow directory handles."""
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parent.parts[1:]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def edit(document, client, role, action, values, fields, settings_path, cwd, stage=None):
    document = validate(document)
    entry = document['clients'].setdefault(client, {})
    if stage is not None:
        parent, key = entry.setdefault('stages', {}).setdefault(stage, {}), role
    elif role is None:
        parent, key = entry, 'defaults'
    else:
        parent, key = entry.setdefault('roles', {}), role
    if action == 'set':
        updated = normalize(values)
        require(bool(updated), 'Set requires at least one field')
        pins(updated, allow_policy=role is None)
        if updated.get('policy') is not None:
            updated['policy'] = os.path.relpath(absolute(updated['policy'], cwd), settings_path.parent)
        parent.setdefault(key, {}).update(updated)
    elif action == 'reset':
        if fields:
            require(set(fields) <= (FIELDS if role is None else FIELDS - {'policy'}), 'Invalid reset field')
            for field in fields:
                parent.get(key, {}).pop(field, None)
        else:
            parent.pop(key, None)
    else:
        raise SettingsError('Action must be set or reset')
    if not parent.get(key):
        parent.pop(key, None)
    if not entry.get('roles'):
        entry.pop('roles', None)
    for phase in list(entry.get('stages', {})):
        if not entry['stages'][phase]:
            entry['stages'].pop(phase)
    if not entry.get('stages'):
        entry.pop('stages', None)
    if not entry:
        document['clients'].pop(client, None)
    return validate(document)


def atomic_write(path, parent, raw, document):
    token = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex
    temporary = f'.{path.name}.{token}.tmp'
    backup = f'{path.name}.backup-{token}' if raw is not None else None
    def write(name, content):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    try:
        try:
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            current = None
        require(current is None or stat.S_ISREG(current.st_mode), f'Settings target changed to a nonregular file: {path}')
        write(temporary, (json.dumps(document, indent=2) + '\n').encode())
        if backup:
            write(backup, raw)
        # Replacement targets the entry itself, never follows a symlink.
        os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
    return str(path.parent / backup) if backup else None


def batch_operations(operations):
    require(isinstance(operations, list) and bool(operations), 'Batch requires a nonempty operations list')
    normalized, targets = [], set()
    for operation in operations:
        require(isinstance(operation, dict) and not set(operation) - {'action', 'stage', 'role', 'values', 'fields'}, 'Invalid batch operation keys')
        action = operation.get('action')
        require(action in ('set', 'reset'), 'Operation action must be set or reset')
        stage = stage_name(operation.get('stage'))
        role = role_name(operation['role']) if operation.get('role') is not None else None
        require(stage is None or role is not None, 'Stage editing requires a role')
        require((stage, role) not in targets, 'Duplicate stage/role target in batch')
        targets.add((stage, role))
        values, fields = operation.get('values') or {}, operation.get('fields')
        require(isinstance(values, dict), 'Operation values must be an object')
        require(fields is None or (isinstance(fields, list) and all(isinstance(field, str) for field in fields)), 'Reset fields must be a list of field names')
        if action == 'set':
            require(not fields, 'Set does not accept reset fields')
            require(bool(values), 'Set requires at least one field')
            pins(values, allow_policy=role is None)
        else:
            require(not values, 'Reset does not accept pin values')
            require(not fields or set(fields) <= (FIELDS if role is None else FIELDS - {'policy'}), 'Invalid reset field')
        normalized.append({'action': action, 'stage': stage, 'role': role, 'values': values, 'fields': fields})
    return normalized


def configure_batch(client, scope, operations, *, apply=False, project=None, user_config=None,
                    no_project=False, trust_project=False, cwd=None):
    """Validate all final edits, then persist one locked transaction and one backup."""
    require(client in ('codex', 'claude') and scope in ('user', 'project'), 'Invalid client/scope')
    operations = batch_operations(operations)
    user, project_path, warnings, cwd = locations(project, user_config, no_project, trust_project, cwd)
    require(scope != 'project' or project_path is not None, 'Project writes require explicit --project or --trust-project inside Git; --no-project-settings disables them')
    target = user if scope == 'user' else project_path
    safe_path(target)
    lock_path = target.with_name(target.name + '.lock')
    safe_path(lock_path)
    documents = {path: read_document(path)[0] for path in (user, project_path) if path is not None}

    def prepared(current):
        candidate = current
        for operation in operations:
            candidate = edit(candidate, client, operation['role'], operation['action'],
                             operation['values'], operation['fields'], target, cwd, operation['stage'])
        results = []
        for operation in operations:
            role, stage = operation['role'], operation['stage']
            # Validate the edited entry before higher-scope or same-scope masks.
            scoped_candidate = validate(candidate)
            entry = scoped_candidate.get('clients', {}).get(client, {})
            if role is None:
                entry.pop('roles', None)
                entry.pop('stages', None)
            elif stage is None:
                entry.pop('stages', None)
            scoped_project = None if scope == 'user' else project_path
            scoped = {**documents, target: scoped_candidate}
            assemble(client, role or 'implementation-worker', user, scoped_project, scoped, None, [], cwd, stage)
            staged = {**documents, target: candidate}
            resolved = assemble(client, role or 'implementation-worker', user, project_path, staged, None, warnings, cwd, stage)
            resolved.update(stage=stage, role=role, action=operation['action'])
            results.append(resolved)
        return candidate, results

    candidate, results = prepared(documents[target])
    result = {'results': results, 'settings_path': str(target), 'action': 'batch', 'applied': False, 'backup': None}
    if not apply:
        return result
    with open_parent(target) as parent:
        lock = os.open(lock_path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            require(stat.S_ISREG(os.fstat(lock).st_mode), 'Settings lock must be a regular file')
            fcntl.flock(lock, fcntl.LOCK_EX)
            current, raw = read_document(target, parent)
            for path in documents:
                if path != target:
                    documents[path] = read_document(path)[0]
            candidate, results = prepared(current)
            backup = atomic_write(target, parent, raw, candidate) if candidate != current else None
            result.update(results=results, applied=candidate != current, backup=backup)
            return result
        finally:
            os.close(lock)


def configure(client, action, scope, *, role=None, stage=None, values=None, fields=None, apply=False,
              project=None, user_config=None, no_project=False, trust_project=False, cwd=None):
    """Legacy single-entry wrapper around the atomic batch API."""
    batch = configure_batch(client, scope, [{'action': action, 'stage': stage, 'role': role,
                                            'values': values, 'fields': fields}],
                            apply=apply, project=project, user_config=user_config,
                            no_project=no_project, trust_project=trust_project, cwd=cwd)
    return {**batch['results'][0], **{key: batch[key] for key in ('settings_path', 'applied', 'backup')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'set', 'reset'))
    parser.add_argument('--client', choices=('codex', 'claude'), required=True)
    parser.add_argument('--scope', choices=('user', 'project'))
    parser.add_argument('--role')
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--tier', choices=('auto', *TIERS))
    parser.add_argument('--model')
    parser.add_argument('--effort')
    parser.add_argument('--max-tier', choices=TIERS)
    parser.add_argument('--policy')
    parser.add_argument('--field', action='append', choices=sorted(FIELDS))
    parser.add_argument('--project', type=Path)
    parser.add_argument('--user-config', type=Path)
    parser.add_argument('--trust-project', action='store_true')
    parser.add_argument('--no-project-settings', dest='no_project', action='store_true')
    parser.add_argument('--apply', action='store_true', help='Persist changes; default previews only')
    args = vars(parser.parse_args())
    try:
        action, scope, apply = args.pop('action'), args.pop('scope'), args.pop('apply')
        fields = args.pop('field')
        values = {key: args.pop(key) for key in ('tier', 'model', 'effort', 'max_tier', 'policy')}
        values = {key: value for key, value in values.items() if value is not None}
        if action == 'status':
            require(not values and not fields and scope is None and not apply, 'Status does not accept write fields/scope/apply')
            args['role'] = args['role'] or 'implementation-worker'
            result = resolve(**args)
        else:
            require(scope is not None, 'Set/reset requires --scope')
            require(action != 'reset' or not values, 'Reset uses --field, not pin values')
            require(action != 'set' or not fields, 'Set does not accept --field')
            result = configure(action=action, scope=scope, apply=apply, values=values, fields=fields, **args)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, TypeError, subprocess.SubprocessError) as exc:
        print(f'Model settings rejected: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
