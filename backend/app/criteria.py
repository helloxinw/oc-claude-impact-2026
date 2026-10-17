"""A flat index of the IHH admission-criteria rules (backend/app/data/admission_criteria.json):
each rule's kind and whether it applies to every patient or only to one condition group. Used to
tell the classifier exactly which rules it must cover, and to check its answer afterwards.
"""
from dataclasses import dataclass
from typing import Any

# `rules` sections screened for every patient, regardless of diagnosis. Every other `rules` section
# (Diabetes, Infection, Respiratory Illness, Cardiac) and every `by_system` system is a condition
# group that only applies when the patient has that condition.
ALWAYS_APPLICABLE_SECTIONS = (
    'ADLs', 'Mobility', 'Mental Health', 'Cognition', 'Other Factors', 'End of life care', 'Infection Control',
)
# Referral-form exclusions the outline is silent on, so the form's rule applies (see `precedence`).
ALWAYS_APPLICABLE_FORM_RULES = ('FORM-X4', 'FORM-X5')

# Kinds that never get a pass/fail verdict: `ask` items are answered in question_answers, and
# `note` items are context (the human_review ones surface as flags_for_human_review instead).
UNSCORED_KINDS = ('ask', 'note')


@dataclass(frozen=True)
class RuleInfo:
    id: str
    text: str
    # One of the outline's kinds (must, exclude, document, conditional, ask, note), plus 'any_of'
    # for the `general` rules and 'eligible' for a by_system eligible condition with no kind of its own.
    kind: str
    # None when the rule applies to every patient; otherwise the condition group (a `rules` section
    # or a `by_system` system name) it is scoped to.
    group: str | None
    # True for by_system entries: a list of specific conditions, so only the ones that could match
    # this patient's diagnosis need a verdict (the rest are implicitly not applicable).
    by_system: bool = False


def rule_index(criteria: dict[str, Any]) -> dict[str, RuleInfo]:
    index: dict[str, RuleInfo] = {}
    for rule in criteria['general']['any_of']:
        index[rule['id']] = RuleInfo(rule['id'], rule['text'], 'any_of', None)
    for rule in criteria['rules']:
        group = None if rule['section'] in ALWAYS_APPLICABLE_SECTIONS else rule['section']
        index[rule['id']] = RuleInfo(rule['id'], rule['text'], rule['kind'], group)
    for system in criteria['by_system']:
        for rule in system['eligible']:
            index[rule['id']] = RuleInfo(rule['id'], rule['text'], rule.get('kind', 'eligible'), system['system'], by_system=True)
        for rule in system['ineligible']:
            index[rule['id']] = RuleInfo(rule['id'], rule['text'], rule.get('kind', 'exclude'), system['system'], by_system=True)
    for rule in criteria['referral_form_screen']['not_eligible_if']:
        if rule['id'] in ALWAYS_APPLICABLE_FORM_RULES:
            index[rule['id']] = RuleInfo(rule['id'], rule['text'], 'exclude', None)
    return index


def condition_groups(criteria: dict[str, Any]) -> list[str]:
    """Every condition group name, in outline order: the diagnosis-specific `rules` sections, then
    the `by_system` systems."""
    groups: list[str] = []
    for rule in criteria['rules']:
        if rule['section'] not in ALWAYS_APPLICABLE_SECTIONS and rule['section'] not in groups:
            groups.append(rule['section'])
    groups.extend(system['system'] for system in criteria['by_system'])
    return groups


def always_applicable_rule_ids(index: dict[str, RuleInfo]) -> list[str]:
    """Rules every patient must get a verdict on, whatever their diagnosis."""
    return [r.id for r in index.values() if r.group is None and r.kind not in UNSCORED_KINDS]
