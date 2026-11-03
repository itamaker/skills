#!/usr/bin/env python3
"""Plan a task's requested model/effort without dispatching or making model calls."""

import argparse
import importlib.util
from collections.abc import Mapping
import json
import os
import runpy
from pathlib import Path
import re
import sys


TIERS = ('economy', 'balanced', 'deep')
_REGISTRY = runpy.run_path(str(Path(__file__).resolve().with_name('stage_registry.py')))
ROLES = _REGISTRY['ROLES']
CLAUDE_SPAWN_ALIASES = {'haiku', 'sonnet', 'opus', 'fable'}


class PolicyError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PolicyError(message)


def role_minimums(auto):
    values = auto.get('role_minimums')
    require(isinstance(values, dict), 'Policy auto.role_minimums must be an object')
    normalized = {}
    for role, tier in values.items():
        name = _REGISTRY['role_name'](role)
        require(name not in normalized and tier in TIERS, 'Duplicate or invalid role minimum')
        normalized[name] = tier
    require(set(ROLES[:6]) <= set(normalized), 'Policy is missing a core role minimum')
    for role in ROLES[6:]:
        normalized.setdefault(role, 'balanced')
    return normalized


def validate_policy(policy):
    require(isinstance(policy, dict) and type(policy.get('version')) is int and policy.get('version') == 1, 'Policy requires version 1')
    auto = policy.get('auto', {})
    require(isinstance(auto, dict), 'Policy auto must be an object')
    role_minimums(auto)
    for key, expected in [('complexity', ('low', 'medium', 'high')), ('risk', ('low', 'medium', 'high'))]:
        values = auto.get(key)
        require(isinstance(values, dict) and set(values) == set(expected), f'Policy auto.{key} has invalid keys')
        require(all(tier in TIERS for tier in values.values()), f'Policy auto.{key} has invalid tiers')
    clients = policy.get('clients')
    require(isinstance(clients, dict) and set(clients) == {'codex', 'claude'}, 'Policy requires codex and claude clients')
    for client, settings in clients.items():
        require(isinstance(settings, dict), f'Invalid settings for {client}')
        tiers, capabilities = settings.get('tiers'), settings.get('model_capabilities')
        require(isinstance(tiers, dict) and set(tiers) == set(TIERS), f'Invalid tiers for {client}')
        require(isinstance(capabilities, dict) and capabilities, f'Missing model capabilities for {client}')
        for model, cap in capabilities.items():
            require(isinstance(model, str) and bool(model.strip()) and isinstance(cap, dict), 'Invalid model capability record')
            efforts = cap.get('efforts')
            require(isinstance(efforts, list) and efforts and all(isinstance(e, str) and bool(e.strip()) for e in efforts), f'Invalid efforts for {model}')
            require(len(efforts) == len(set(efforts)), f'Duplicate efforts for {model}')
            require(cap.get('default_effort') in efforts, f'Invalid default_effort for {model}')
            require(cap.get('tier') in TIERS and isinstance(cap.get('vision'), bool), f'Missing tier/vision capability for {model}')
        for tier, pair in tiers.items():
            require(isinstance(pair, dict), f'Invalid {client}/{tier} model pair')
            model = pair.get('model')
            require(isinstance(model, str) and model in capabilities, f'Unknown model in {client}/{tier}')
            cap = capabilities[model]
            require(pair.get('effort') in cap['efforts'], f'Unsupported effort in {client}/{tier}')
            require(cap['tier'] == tier, f'Model tier conflicts with {client}/{tier}')
    return policy


def load_policy(path=None):
    path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / 'assets/model-policy.json'
    with path.open(encoding='utf-8') as stream:
        return validate_policy(json.load(stream))


def claude_constraints(runtime, version, model, env, warnings):
    constraints = []
    if runtime == 'spawn':
        if model not in CLAUDE_SPAWN_ALIASES:
            constraints.append('Claude invocation model overrides accept supported aliases only; use a session preset for full model IDs')
        parsed = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?: \(Claude Code\))?', version or '')
        if not parsed or tuple(map(int, parsed.groups())) < (2, 1, 292):
            constraints.append('Claude invocation effort overrides require a verified version >=2.1.292')
    force = str(env.get('CLAUDE_CODE_SUBAGENT_MODEL_FORCE', '')).strip().lower()
    if force in ('1', 'true', 'yes', 'on'):
        constraints.append('CLAUDE_CODE_SUBAGENT_MODEL_FORCE controls subagent model selection; resolve the environment before applying this plan')
    effort = str(env.get('CLAUDE_CODE_EFFORT_LEVEL', '')).strip().lower()
    if effort:
        if effort in ('auto', 'unset'):
            constraints.append('CLAUDE_CODE_EFFORT_LEVEL suppresses the effort parameter and uses the API default; resolve the environment before applying requested effort')
        else:
            constraints.append('CLAUDE_CODE_EFFORT_LEVEL overrides requested effort; resolve the environment before applying this plan')
    for key in ('ANTHROPIC_MODEL', 'CLAUDE_CODE_SUBAGENT_MODEL',
                'ANTHROPIC_DEFAULT_HAIKU_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL',
                'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_FABLE_MODEL'):
        if env.get(key):
            warnings.append(f'{key} affects defaults/alias resolution; observe the actual runtime model')
    return constraints


def select(policy, client, role='implementation-worker', complexity='medium', risk='low',
           tier='auto', model=None, effort=None, max_tier='deep', escalate=False,
           escalation_count=0, evidence=None, runtime='unknown', claude_version=None, env=None):
    """runtime=spawn asserts the caller verified model+effort override fields in its host schema."""
    validate_policy(policy)
    require(client in ('codex', 'claude'), 'Unknown client')
    require(isinstance(role, str), 'Role must be a string')
    role = role.replace('_', '-')
    require(role in ROLES, 'Unknown role')
    require(complexity in ('low', 'medium', 'high') and risk in ('low', 'medium', 'high'), 'Invalid complexity/risk')
    require(tier in (*TIERS, 'auto') and max_tier in TIERS, 'Invalid tier/max_tier')
    require(runtime in ('unknown', 'fixed', 'spawn', 'session'), 'Invalid runtime')
    require(type(escalate) is bool and type(escalation_count) is int and escalation_count in (0, 1), 'Escalation count must be 0 or 1')
    require(model is None or (isinstance(model, str) and bool(model.strip())), 'Model must be a nonempty string')
    require(effort is None or (isinstance(effort, str) and bool(effort.strip())), 'Effort must be a nonempty string')
    require(claude_version is None or isinstance(claude_version, str), 'Claude version must be a string')
    env = os.environ if env is None else env
    require(isinstance(env, Mapping), 'Environment must be a mapping')
    auto = policy['auto']
    recommended = max((role_minimums(auto)[role], auto['complexity'][complexity], auto['risk'][risk]), key=TIERS.index)
    selected_tier = recommended if tier == 'auto' else tier
    settings = policy['clients'][client]
    capabilities = settings['model_capabilities']
    warnings = []
    reasons = [f'{role}, {complexity} complexity, {risk} risk recommend {recommended}']
    if model is not None:
        require(model in capabilities, f'Unknown model {model}; add an explicit capability record to the policy')
        actual_tier = capabilities[model]['tier']
        require(tier == 'auto' or actual_tier == tier, 'Explicit model conflicts with explicit tier')
        selected_tier = actual_tier
        reasons.append('Explicit model override')
    elif tier != 'auto':
        reasons.append('Explicit tier override')
    if escalate:
        require(tier == 'auto' and model is None and effort is None, 'Automatic escalation cannot override explicit tier/model/effort pins')
        require(escalation_count == 0, 'Only one escalation is allowed per milestone')
        require(isinstance(evidence, str) and bool(evidence.strip()), 'Escalation requires nonempty failure/uncertainty evidence')
        require(selected_tier != 'deep', 'Already at the highest tier; return evidence to the coordinator')
        selected_tier = TIERS[TIERS.index(selected_tier) + 1]
        escalation_count += 1
        reasons.append('One evidence-backed escalation')
    require(TIERS.index(selected_tier) <= TIERS.index(max_tier), f'Requested {selected_tier} exceeds hard cap {max_tier}; resolve the conflict explicitly')
    if TIERS.index(selected_tier) < TIERS.index(recommended):
        warnings.append(f'Explicit selection {selected_tier} is below recommended {recommended}')
    if role == 'visual-advisor' and tier == 'auto' and model is None:
        candidates = [candidate for candidate in TIERS[TIERS.index(selected_tier):]
                      if TIERS.index(candidate) <= TIERS.index(max_tier)
                      and capabilities[settings['tiers'][candidate]['model']]['vision']]
        require(candidates, 'No vision-capable automatic selection satisfies the recommended tier and hard cap')
        if candidates[0] != selected_tier:
            selected_tier = candidates[0]
            reasons.append(f'Vision capability requires {selected_tier}')
    pair = settings['tiers'][selected_tier]
    requested_model = model if model is not None else pair['model']
    cap = capabilities[requested_model]
    requested_effort = effort if effort is not None else (cap['default_effort'] if model is not None else pair['effort'])
    require(requested_effort in cap['efforts'], f'Effort {requested_effort} is unsupported by {requested_model}; no substitution was made')
    if effort is not None:
        reasons.append('Explicit effort override')
    require(role != 'visual-advisor' or cap['vision'], f'{requested_model} lacks the required vision capability')
    method = {'unknown': 'plan_only', 'fixed': 'session_preset_required', 'spawn': 'spawn_overrides', 'session': 'session_preset'}[runtime]
    constraints = []
    if runtime == 'fixed':
        constraints.append('Fixed host cannot change model/effort per task; start a compatible session preset')
    if client == 'claude':
        constraints.extend(claude_constraints(runtime, claude_version, requested_model, env, warnings))
        if constraints and runtime != 'unknown':
            method = 'session_preset_required'
    warnings.append('Policy aliases/tiers are examples; account availability, pricing and applied runtime settings remain unverified')
    return {
        'requested_model': requested_model, 'requested_effort': requested_effort,
        'tier': selected_tier, 'recommended_tier': recommended, 'reason': '; '.join(reasons),
        'warnings': warnings, 'constraints': constraints, 'application_method': method,
        'effective_model': None, 'effective_effort': None,
        'escalation_count': escalation_count, 'max_escalations': 1,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--client', required=True, choices=('codex', 'claude'))
    parser.add_argument('--role', default='implementation-worker')
    parser.add_argument('--stage', help='Actual workflow stage; omitted preserves generic role defaults')
    parser.add_argument('--complexity', choices=('low', 'medium', 'high'), default='medium')
    parser.add_argument('--risk', choices=('low', 'medium', 'high'), default='low')
    parser.add_argument('--tier', choices=('auto', *TIERS))
    parser.add_argument('--model')
    parser.add_argument('--effort')
    parser.add_argument('--max-tier', choices=TIERS)
    parser.add_argument('--project', type=Path, help='Use settings from this authorized project')
    parser.add_argument('--user-config', type=Path, help='Alternate personal settings file')
    parser.add_argument('--trust-project', action='store_true', help='Use discovered Git-project settings only after establishing workspace trust')
    parser.add_argument('--no-project-settings', action='store_true', help='Ignore project settings while retaining personal defaults')
    parser.add_argument('--escalate', action='store_true')
    parser.add_argument('--escalation-count', type=int, default=0)
    parser.add_argument('--evidence')
    parser.add_argument('--runtime', choices=('unknown', 'fixed', 'spawn', 'session'), default='unknown')
    parser.add_argument('--claude-version')
    args = vars(parser.parse_args())
    try:
        settings_source = Path(__file__).resolve().with_name('model_settings.py')
        spec = importlib.util.spec_from_file_location('shipyard_model_settings', settings_source)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)
        overrides = {key: value for key in ('tier', 'model', 'effort', 'max_tier', 'policy')
                     if (value := args.pop(key)) is not None}
        if 'policy' in overrides:
            overrides['policy'] = str(overrides['policy'])
        resolved = settings_module.resolve(
            args['client'], args['role'], project=args.pop('project'),
            user_config=args.pop('user_config'), trust_project=args.pop('trust_project'),
            no_project=args.pop('no_project_settings'), overrides=overrides, stage=args.pop('stage'),
        )
        policy = load_policy(resolved['policy_path'])
        args.update(resolved['values'])
        result = select(policy, **args)
        result['warnings'] = list(dict.fromkeys([*resolved['warnings'], *result['warnings']]))
        result['settings'] = {
            key: resolved[key] for key in ('policy_path', 'sources', 'layers', 'ceiling_sources', 'stage', 'role')
        }
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, TypeError, ImportError) as exc:
        print(f'Model plan rejected: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
