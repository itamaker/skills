"""Shared personal Markdown personas and atomic role selections for both clients."""

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import runpy
import stat
import uuid


SCRIPT = Path(__file__).resolve().parent
BUILTINS = SCRIPT.parent / 'references/personas'
REGISTRY = runpy.run_path(str(SCRIPT / 'stage_registry.py'))
ROLES = REGISTRY['ROLES']
role_name = REGISTRY['role_name']
spec = importlib.util.spec_from_file_location('persona_storage', SCRIPT / 'model_settings.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


def profile_id(value):
    storage.require(isinstance(value, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value)
                    and len(value) <= 64, 'Profile ID must use lowercase ASCII letters, digits and single hyphens (maximum 64 characters)')
    return value


def locations():
    xdg = os.environ.get('XDG_CONFIG_HOME')
    storage.require(not xdg or Path(xdg).is_absolute(), 'XDG_CONFIG_HOME must be absolute')
    root = (Path(xdg) if xdg else Path.home() / '.config') / 'shipyard'
    return root / 'persona-settings.json', root / 'personas'


def read_profile(path, source):
    storage.safe_path(path)
    with path.open(encoding='utf-8') as stream:
        content = stream.read()
    lines = [line for line in content.splitlines() if line.strip()]
    storage.require(len(lines) >= 3 and lines[0].startswith('# ') and lines[1].startswith('ID: '),
                    f'Profile needs a title, ID and behavioral content: {path}')
    name = lines[0][2:].strip()
    identity = profile_id(lines[1][4:].strip())
    storage.require(bool(name), f'Profile name is empty: {path}')
    if source == 'user':
        storage.require(path.stem == identity, f'Profile ID must match its filename: {path}')
    return {'id': identity, 'name': name, 'path': str(path.absolute()),
            'source': source, 'content': content}


def catalog(profiles_dir):
    profiles, defaults = {}, {}
    for path in sorted(BUILTINS.glob('*.md')) + sorted((BUILTINS / 'alternatives').glob('*.md')):
        profile = read_profile(path, 'builtin')
        storage.require(profile['id'] not in profiles, f'Duplicate profile ID: {profile["id"]}')
        profiles[profile['id']] = profile
        if path.parent == BUILTINS and path.stem in ROLES:
            defaults[path.stem] = profile['id']
    storage.require(set(defaults) == set(ROLES), 'Built-in profiles must cover all nine roles')
    storage.safe_path(profiles_dir / '.profile-check')
    errors = {}
    for path in sorted(profiles_dir.glob('*.md')):
        try:
            profile = read_profile(path, 'user')
            storage.require(profile['id'] not in profiles, f'Duplicate profile ID: {profile["id"]}')
            profiles[profile['id']] = profile
        except (ValueError, OSError) as error:
            errors[path.stem] = str(error)
    return profiles, defaults, errors


def read_settings(path, parent=None):
    if parent is None:
        storage.safe_path(path)
    try:
        fd = os.open(path.name if parent is not None else path,
                     os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        return {'version': 1, 'roles': {}}, None
    with os.fdopen(fd, 'rb') as stream:
        storage.require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'Persona settings must be a regular file')
        raw = stream.read()
    document = json.loads(raw, object_pairs_hook=storage.unique_object)
    storage.require(isinstance(document, dict) and set(document) == {'version', 'roles'}
                    and type(document['version']) is int and document['version'] == 1
                    and isinstance(document['roles'], dict), 'Invalid persona settings document')
    for role, identity in document['roles'].items():
        storage.require(role in ROLES, f'Unknown saved persona role: {role}')
        profile_id(identity)
    return document, raw


def selected(role, document, profiles, defaults):
    identity = document['roles'].get(role, defaults[role])
    storage.require(identity in profiles, f'Selected profile is missing for {role}: {identity}; restore its Markdown file or reset this role')
    return {'role': role, 'profile': profiles[identity],
            'selection': 'saved' if role in document['roles'] else 'default'}


def save_selection(path, role, identity, preview):
    def changed(document):
        document = {'version': 1, 'roles': dict(document['roles'])}
        if identity is None:
            document['roles'].pop(role, None)
        else:
            document['roles'][role] = identity
        return document

    current, raw = read_settings(path)
    candidate = changed(current)
    if preview:
        return candidate, False, None
    lock_path = path.with_name(path.name + '.lock')
    storage.safe_path(lock_path)
    with storage.open_parent(path) as parent:
        fd = os.open(lock_path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            storage.require(stat.S_ISREG(os.fstat(fd).st_mode), 'Persona lock must be a regular file')
            fcntl.flock(fd, fcntl.LOCK_EX)
            current, raw = read_settings(path, parent)
            candidate = changed(current)
            backup = storage.atomic_write(path, parent, raw, candidate) if candidate != current else None
            return candidate, candidate != current, backup
        finally:
            os.close(fd)


def create_profile(path, content, preview):
    storage.safe_path(path)
    storage.require(not path.exists(), f'Profile already exists; edit its Markdown file: {path}')
    if preview:
        return
    with storage.open_parent(path) as parent:
        temporary = f'.{path.name}.{uuid.uuid4().hex}.tmp'
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            # Publish a complete file while preserving concurrent creations.
            os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.fsync(parent)
        finally:
            os.unlink(temporary, dir_fd=parent)


def handle(args):
    model_flags = any(getattr(args, target.replace('-', '_')) is not None for target in REGISTRY['TARGETS'])
    storage.require(not (model_flags or args.config or args.reset is not None or args.task or args.next
                         or args.user_config is not None or args.no_project_settings),
                    'Persona commands use personal cross-client scope; run model/task/next configuration separately')
    operations = [args.personas, args.persona_show, args.persona, args.persona_create, args.persona_reset]
    storage.require(sum(bool(value) for value in operations) == 1, 'Specify one persona operation')
    storage.require(args.persona_create is not None or (args.name is None and args.traits is None),
                    '--name and --traits require --persona-create')
    storage.require(not args.preview or args.persona is not None or args.persona_reset is not None
                    or args.persona_create is not None, '--preview requires a persona mutation')
    role, identity = None, None
    if args.persona is not None:
        role, separator, identity = args.persona.partition(':')
        storage.require(bool(separator), '--persona requires ROLE:ID')
        role, identity = role_name(role), profile_id(identity)
    elif args.persona_show is not None or args.persona_reset is not None:
        role = role_name(args.persona_show or args.persona_reset)
    if args.persona_create is not None:
        identity = profile_id(args.persona_create)
        storage.require(isinstance(args.name, str) and bool(args.name.strip())
                        and '\n' not in args.name and '\r' not in args.name, 'A nonempty single-line --name is required')
        storage.require(isinstance(args.traits, str) and bool(args.traits.strip()), 'Nonempty --traits are required')
    path, profiles_dir = locations()
    profiles, defaults, errors = catalog(profiles_dir)
    document, _ = read_settings(path)
    common = {'scope': 'user', 'settings_path': str(path), 'profiles_dir': str(profiles_dir),
              'applied': False, 'preview': args.preview}
    if args.personas:
        entries = [{key: value for key, value in profile.items() if key != 'content'}
                   for profile in profiles.values()]
        roles = []
        for name in ROLES:
            chosen = document['roles'].get(name, defaults[name])
            entry = {'role': name, 'id': chosen, 'selection': 'saved' if name in document['roles'] else 'default'}
            if chosen not in profiles:
                entry['error'] = errors.get(chosen, f'Missing profile: {chosen}')
            roles.append(entry)
        return {**common, 'mode': 'persona_list', 'profiles': entries, 'roles': roles, 'errors': errors}
    if args.persona_show:
        chosen = document['roles'].get(role, defaults[role])
        if chosen in errors and chosen not in profiles:
            raise ValueError(errors[chosen])
        return {**common, 'mode': 'persona_show', **selected(role, document, profiles, defaults)}
    if args.persona_create:
        storage.require(identity not in profiles, f'Profile ID already exists: {identity}')
        target = profiles_dir / f'{identity}.md'
        content = f'# {args.name.strip()}\n\nID: {identity}\n\n## Behavioral traits\n\n{args.traits.strip()}\n'
        create_profile(target, content, args.preview)
        profile = {'id': identity, 'name': args.name.strip(), 'path': str(target), 'source': 'user', 'content': content}
        return {**common, 'mode': 'persona_create', 'applied': not args.preview, 'profile': profile}
    if args.persona is not None:
        storage.require(identity in profiles, errors.get(identity, f'Unknown profile ID: {identity}'))
    document, applied, backup = save_selection(path, role, identity, args.preview)
    return {**common, 'mode': 'persona_settings', 'applied': applied, 'backup': backup,
            **selected(role, document, profiles, defaults), 'application': 'requires_profile_read'}
