"""Tests for scripts/check_lessons.py (frontmatter format).

Loads the script by file path, following the neighbouring test files.
"""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'check_lessons.py'
spec = importlib.util.spec_from_file_location('check_lessons', SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

LESSONS_DIR = Path(__file__).resolve().parents[2] / 'references' / 'lessons'

VALID = """\
---
lessons:
  - id: pm-001
    added: 2026-11-22
    status: active
---

# Project-manager lessons

## [pm-001] Confirm acceptance before starting work

- Trigger: A ticket is assigned and its acceptance criteria are unclear.
- Pattern: Starting work and discovering the real acceptance halfway through.
- Do instead: Confirm the acceptance criteria with the coordinator before writing code.
- Why: Rework costs more than a question asked up front.
"""

RETIRED = VALID.replace(
    "    status: active",
    "    status: retired\n    retired: 2026-11-22\n"
    "    retired_reason: Later evidence showed the opposite, so the premise was wrong.",
    1)


class CheckLessonsTests(unittest.TestCase):
    def write(self, directory, text, name='project-manager.md'):
        path = Path(directory) / name
        path.write_text(text, encoding='utf-8')
        return path

    def check(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = checker.check_file(self.write(tmp, text), **kwargs)
            return errors

    def assert_error(self, errors, fragment):
        self.assertTrue(any(fragment in error for error in errors),
                        f"expected {fragment!r} in {errors}")

    def test_role_files_pass(self):
        # The shipped role files must pass the checker. The lesson
        # count is whatever rounds have filed so far; it is not
        # fixed — lessons accumulate over rounds, so assert the
        # file count (nine) and that every file passes, not a
        # particular total.
        total, count = 0, 0
        for path in sorted(LESSONS_DIR.glob('*.md')):
            with self.subTest(path=path.name):
                errors, lessons = checker.check_file(path)
                self.assertEqual(errors, [])
                total += lessons
                count += 1
        self.assertEqual(count, 9)

    def test_main_returns_zero_on_shipped_files(self):
        self.assertEqual(checker.main([str(LESSONS_DIR)]), 0)

    def test_main_returns_one_on_bad_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, VALID.replace('    status: active\n', ''))
            self.assertEqual(checker.main([tmp]), 1)

    def test_missing_status(self):
        self.assert_error(self.check(VALID.replace('    status: active\n', '')),
                          'missing status')

    def test_invalid_status(self):
        self.assert_error(self.check(VALID.replace('status: active', 'status: pending')),
                          'status must be active or retired')

    def test_retired_entry_with_date_and_reason_passes(self):
        self.assertEqual(self.check(RETIRED), [])

    def test_retired_without_date_and_reason(self):
        text = VALID.replace('    status: active', '    status: retired', 1)
        errors = self.check(text)
        self.assert_error(errors, 'needs a retired date')
        self.assert_error(errors, 'needs a retired_reason')

    def test_retired_before_added(self):
        text = RETIRED.replace('retired: 2026-11-22', 'retired: 2026-11-21', 1)
        self.assert_error(self.check(text), 'retired date is before added date')

    def test_retired_reason_too_short(self):
        text = RETIRED.replace('Later evidence showed the opposite, so the premise was wrong.',
                               'wrong', 1)
        self.assert_error(self.check(text), 'needs a retired_reason')

    def test_active_entry_must_not_carry_retired_fields(self):
        text = VALID.replace('    status: active',
                             '    status: active\n    retired: 2026-11-22', 1)
        self.assert_error(self.check(text), 'must not carry retired')

    def test_duplicate_ids(self):
        text = VALID.replace(
            '  - id: pm-001\n    added: 2026-11-22\n    status: active\n',
            '  - id: pm-001\n    added: 2026-11-22\n    status: active\n'
            '  - id: pm-001\n    added: 2026-11-22\n    status: active\n', 1)
        self.assert_error(self.check(text), 'duplicate id')

    def test_wrong_id_prefix(self):
        self.assert_error(self.check(VALID.replace('pm-001', 'xx-001')),
                          'must look like pm-NNN')

    def test_frontmatter_entries_without_body(self):
        text = VALID.split('## [pm-001]')[0]
        self.assert_error(self.check(text), 'do not match body sections')

    def test_body_section_without_frontmatter_entry(self):
        text = VALID.replace('  - id: pm-001\n    added: 2026-11-22\n    status: active\n', '')
        self.assert_error(self.check(text), 'do not match body sections')

    def test_body_missing_field(self):
        text = VALID.replace('- Why: Rework costs more than a question asked up front.\n', '')
        self.assert_error(self.check(text), 'missing Why line')

    def test_body_wrong_field_order(self):
        text = VALID.replace('- Trigger: A ticket', '- Pattern: A ticket', 1)
        text = text.replace('- Pattern: Starting work', '- Trigger: Starting work', 1)
        self.assert_error(self.check(text), 'expected Trigger')

    def test_banned_absolute_path(self):
        self.assert_error(self.check(VALID.replace('Rework costs more than a question asked up front.',
                                                   'See the file at /opt/acme/x for rework costs.')),
                          'banned absolute path')

    def test_banned_version_number(self):
        self.assert_error(self.check(VALID.replace('Rework costs more than a question asked up front.',
                                                   'Rework costs more in 1.2.3 than a question.')),
                          'banned version-number-like')

    def test_banned_commit_hash_like_hex(self):
        self.assert_error(self.check(VALID.replace('Rework costs more than a question asked up front.',
                                                   'Rework costs more than deadbeef1 questions.')),
                          'banned commit-hash-like hex')

    def test_banned_name_via_ban_flag(self):
        text = VALID.replace('Rework costs more than a question asked up front.',
                             'Rework costs more than the Acme question.')
        self.assertEqual(self.check(text), [])
        errors = self.check(text, extra_names=('Acme',))
        self.assertEqual(len(errors), 1)
        self.assertIn("banned name: 'Acme'", errors[0])
        self.assertNotIn('banned banned name', errors[0])

    def test_stray_heading_before_first_section(self):
        text = VALID.replace('## [pm-001]', '## Notes\n\n## [pm-001]', 1)
        self.assert_error(self.check(text), 'unexpected heading')

    def test_missing_frontmatter(self):
        self.assert_error(self.check(VALID.replace('---\nlessons:\n', '').replace(
            '    status: active\n---\n', '')),
            'missing YAML frontmatter block')

    def test_bad_added_date(self):
        self.assert_error(self.check(VALID.replace('added: 2026-11-22', 'added: 2026-13-40')),
                          'not a YYYY-MM-DD date')

    def test_frontmatter_unknown_key(self):
        text = VALID.replace('    status: active', '    status: active\n    foo: bar', 1)
        self.assert_error(self.check(text), 'unknown key')

    def test_empty_lessons_list_is_valid(self):
        text = VALID.replace('  - id: pm-001\n    added: 2026-11-22\n    status: active\n', '')
        text = text.split('## [pm-001]')[0]
        self.assertEqual(self.check(text), [])


if __name__ == '__main__':
    unittest.main()
