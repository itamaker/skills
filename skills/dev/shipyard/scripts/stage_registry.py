"""Canonical public agent names and the flat phase-configuration targets."""

ROLES = (
    'chief-of-staff', 'project-manager', 'implementation-worker',
    'architecture-advisor', 'code-advisor', 'visual-advisor',
    'verify-worker', 'ci-worker', 'deliver-worker',
)

TARGETS = {
    'plan': ('plan', 'project-manager'),
    'architecture': ('design', 'architecture-advisor'),
    'design-review': ('design', 'visual-advisor'),
    'implement': ('implement', 'implementation-worker'),
    'code-review': ('review', 'code-advisor'),
    'visual-review': ('review', 'visual-advisor'),
    'verify': ('verify', 'verify-worker'),
    'ci': ('ci', 'ci-worker'),
    'deliver': ('deliver', 'deliver-worker'),
}

STAGES = tuple(dict.fromkeys(stage for stage, role in TARGETS.values()))


def role_name(value):
    """Read legacy underscore spellings; always emit the hyphenated name."""
    if not isinstance(value, str) or value.replace('_', '-') not in ROLES:
        raise ValueError(f'Unknown agent role: {value}')
    return value.replace('_', '-')
