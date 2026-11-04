#!/usr/bin/env python3
"""Parse Shipyard's flat stage flags without evaluating user text as shell code."""

import argparse
import importlib.util
import json
from pathlib import Path
import runpy
import shlex
import subprocess
import sys


TARGETS = runpy.run_path(str(Path(__file__).with_name('stage_registry.py')))['TARGETS']
CONTEXT = {'client', 'project', 'user_config', 'trust_project', 'no_project_settings'}


class CommandError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CommandError(message)


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, '_seen_options', set())
        if option_string in seen:
            raise CommandError(f'Duplicate option: {option_string}')
        seen.add(option_string)
        namespace._seen_options = seen
        setattr(namespace, self.dest, True if self.nargs == 0 else values)


def parser():
    result = Parser(description=__doc__, allow_abbrev=False)
    for target, (stage, role) in TARGETS.items():
        result.add_argument(f'--{target}', action=Once, metavar='MODEL:EFFORT|auto',
                            help=f'{stage}: {role}')
    scope = result.add_mutually_exclusive_group()
    for option, description in [('user', 'Save personal defaults instead of this project'),
                                ('task', 'Return an override intent for this task; do not save'),
                                ('next', 'Return a one-shot intent for one matching subagent')]:
        scope.add_argument(f'--{option}', action=Once, nargs=0, default=False, help=description)
    result.add_argument('--config', action=Once, nargs=0, default=False, help='Show all nine stage settings without changing them')
    result.add_argument('--reset', action=Once, metavar='TARGET[,TARGET]|all', help='Remove selected stage overrides and reveal inherited values')
    result.add_argument('--preview', action=Once, nargs=0, default=False, help='Validate without saving or recording an override')
    result.add_argument('--client', choices=('codex', 'claude'), action=Once, help=argparse.SUPPRESS)
    result.add_argument('--project', type=Path, action=Once, help=argparse.SUPPRESS)
    result.add_argument('--user-config', type=Path, action=Once, help=argparse.SUPPRESS)
    result.add_argument('--trust-project', action=Once, nargs=0, default=False, help=argparse.SUPPRESS)
    result.add_argument('--no-project-settings', action=Once, nargs=0, default=False, help=argparse.SUPPRESS)
    return result


def literal_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CommandError(f'Duplicate input key: {key}')
        result[key] = value
    return result


def bridge(text):
    data = json.loads(text, object_pairs_hook=literal_object)
    if not isinstance(data, dict) or set(data) - (CONTEXT | {'arguments'}):
        raise CommandError('Input must contain arguments and recognized host context only')
    if not isinstance(data.get('arguments'), str):
        raise CommandError('Input arguments must be a string')
    for key in CONTEXT:
        if key not in data:
            continue
        expected = bool if key in ('trust_project', 'no_project_settings') else str
        if type(data[key]) is not expected:
            raise CommandError(f'Invalid context value: {key}')
        if expected is str and not data[key].strip():
            raise CommandError(f'Empty context value: {key}')
    if 'client' in data and data['client'] not in ('codex', 'claude'):
        raise CommandError('Unknown host client')
    raw = data['arguments']
    if not raw.strip():
        return [], None
    if not raw.lstrip().startswith('--'):
        return None, raw
    arguments = shlex.split(raw)
    private = {f'--{key.replace("_", "-")}' for key in CONTEXT}
    if any(token.split('=', 1)[0] in private or token == '--input-json' for token in arguments):
        raise CommandError('Host context must be provided by the bridge, not embedded in skill arguments')
    context = []
    for key in sorted(CONTEXT):
        if key in data:
            flag = f'--{key.replace("_", "-")}'
            if isinstance(data[key], bool):
                if data[key]:
                    context.append(flag)
            else:
                context.extend([flag, data[key]])
    return [*context, *arguments], None


def assignment(value):
    if value == 'auto':
        return {'tier': 'auto'}
    model, separator, effort = value.rpartition(':')
    if not separator or not model.strip() or not effort.strip() or model != model.strip() or effort != effort.strip():
        raise CommandError('Expected MODEL:EFFORT or auto')
    return {'model': model, 'effort': effort}


def backend_module():
    spec = importlib.util.spec_from_file_location('shipyard_settings_frontend', Path(__file__).with_name('model_settings.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summary(target, resolved):
    stage, role = TARGETS[target]
    return {'target': target, 'stage': stage, 'agent': role,
            'preferences': resolved['values'],
            'sources': {key: value['layer'] for key, value in resolved['sources'].items()},
            'policy_path': resolved['policy_path'], 'warnings': resolved['warnings']}


def handle(argv, *, backend=None, cwd=None, input_text=None):
    argv = list(argv)
    if argv == ['--input-json']:
        argv, natural = bridge(sys.stdin.read() if input_text is None else input_text)
        if natural is not None:
            return {'mode': 'natural', 'text': natural}
    elif '--input-json' in argv:
        raise CommandError('--input-json must be the only outer option')
    if not argv:
        return {'mode': 'delivery'}
    if not argv[0].startswith('--'):
        return {'mode': 'natural', 'text': ' '.join(argv)}
    command = parser()
    if '--help' in argv:
        return {'mode': 'help', 'text': command.format_help()}
    args = command.parse_args(argv)
    operations, names = [], []
    for target, (stage, role) in TARGETS.items():
        value = getattr(args, target.replace('-', '_'))
        if value is not None:
            operations.append({'action': 'set', 'stage': stage, 'role': role, 'values': assignment(value)})
            names.append(target)
    if args.reset is not None:
        resets = list(TARGETS) if args.reset == 'all' else args.reset.split(',')
        if not resets or len(resets) != len(set(resets)) or any(target not in TARGETS for target in resets):
            raise CommandError('Reset requires unique registered targets or all')
        if set(names) & set(resets):
            raise CommandError('A target cannot be assigned and reset in one command')
        for target in resets:
            stage, role = TARGETS[target]
            operations.append({'action': 'reset', 'stage': stage, 'role': role})
            names.append(target)
    if args.config and (operations or args.preview):
        raise CommandError('--config cannot be mixed with changes or --preview')
    if not args.config and not operations:
        raise CommandError('Specify a stage assignment, --config, --reset, or --help')
    if args.next and sum(operation['action'] == 'set' for operation in operations) > 1:
        raise CommandError('--next accepts only one stage assignment')
    if args.client is None:
        raise CommandError('The host must provide the active client')
    backend = backend or backend_module()
    context = {'project': args.project, 'user_config': args.user_config,
               'no_project': args.no_project_settings or args.user,
               'trust_project': args.trust_project or not args.user, 'cwd': cwd}
    if args.task or args.next:
        mode = 'task' if args.task else 'next'
        if args.config:
            return {'mode': f'{mode}_status_intent', 'client': args.client,
                    'note': 'Read pending overrides from the coordinator task record; no override is consumed.'}
        targets = []
        for target, operation in zip(names, operations):
            if operation['action'] == 'set':
                resolved = backend.resolve(args.client, operation['role'], stage=operation['stage'],
                                           overrides=operation['values'], **context)
                targets.append(summary(target, resolved))
        return {'mode': f'{mode}_override_intent', 'client': args.client,
                'record': not args.preview, 'operations': operations, 'targets': targets,
                'effective_model': None, 'effective_effort': None}
    scope = 'user' if args.user else 'project'
    if args.config:
        targets = [summary(target, backend.resolve(args.client, role, stage=stage, **context))
                   for target, (stage, role) in TARGETS.items()]
        return {'mode': 'config', 'scope': scope, 'client': args.client, 'targets': targets,
                'effective_model': None, 'effective_effort': None}
    batch = backend.configure_batch(args.client, scope, operations, apply=not args.preview, **context)
    return {'mode': 'settings', 'scope': scope, 'client': args.client,
            'applied': batch['applied'], 'preview': args.preview,
            'settings_path': batch['settings_path'], 'backup': batch['backup'],
            'targets': [summary(target, resolved) for target, resolved in zip(names, batch['results'])],
            'effective_model': None, 'effective_effort': None}


def main():
    try:
        result = handle(sys.argv[1:])
        print(result['text'] if result['mode'] == 'help' else json.dumps(result, indent=2))
    except (ValueError, OSError, TypeError, subprocess.SubprocessError) as error:
        print(f'Shipyard arguments rejected: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
