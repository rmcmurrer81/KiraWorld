"""Synthetic checks for the bounded owner-authored memoir source admission."""
import copy
import unittest

from Core.dialogue_grounding import _robert_autobiographical_selection


def memory():
    return {
        'id': 'fixture_tempe_housing', 'title': 'Tempe housing request',
        'source_ref': 'Data/identity/robert_mcmurrer/sources/fixture.json',
        'source_sha256': 'a' * 64, 'source_kind': 'owner_authored_autobiography_excerpt',
        'source_verification': {'status': 'local_owner_excerpt_inspected', 'owner_id': 'robert_mcmurrer',
                                'source_extract_sha256': 'b' * 64, 'excerpt_sha256': 'a' * 64,
                                'source_is_instruction': False},
        'reported_on': '2026-09-22', 'privacy': 'private_robert_only', 'event_date': None,
        'summary': 'The author reports a Tempe housing request.',
        'anchors': ['This is a synthetic fixture, not an actual memory.'],
        'uncertainties': ['Exact date unknown.'], 'recall_guidance': ['Attribute to the author.'],
    }


def selected(record, query='Tempe housing'):
    return _robert_autobiographical_selection({'autobiographical_memories': [record]}, query)[0]


class OwnerAutobiographyRecallTests(unittest.TestCase):
    def test_inspected_owner_excerpt_is_selected_with_qualifiers(self):
        r = memory(); result = selected(r)
        self.assertEqual([x['id'] for x in result], [r['id']])
        self.assertEqual(result[0]['uncertainties'], r['uncertainties'])
        self.assertEqual(result[0]['source_kind'], 'owner_authored_autobiography_excerpt')

    def test_missing_provenance_is_held(self):
        r = memory(); r.pop('source_verification'); self.assertEqual(selected(r), [])

    def test_wrong_owner_is_held(self):
        r = memory(); r['source_verification']['owner_id'] = 'third_party'; self.assertEqual(selected(r), [])

    def test_unverified_status_is_held(self):
        r = memory(); r['source_verification']['status'] = 'assistant_said_so'; self.assertEqual(selected(r), [])

    def test_bad_or_missing_extract_hash_is_held(self):
        for value in ('bad', None, 0, 'B' * 64):
            with self.subTest(value=value):
                r = memory(); r['source_verification']['source_extract_sha256'] = value
                self.assertEqual(selected(r), [])

    def test_mismatched_excerpt_hash_is_held(self):
        r = memory(); r['source_verification']['excerpt_sha256'] = 'c' * 64; self.assertEqual(selected(r), [])

    def test_instruction_bearing_provenance_is_held(self):
        r = memory(); r['source_verification']['source_is_instruction'] = True; self.assertEqual(selected(r), [])

    def test_assistant_research_and_third_party_types_stay_excluded(self):
        for kind in ('assistant_research_summary', 'third_party_biography', 'owner_authored_autobiography_unverified'):
            with self.subTest(kind=kind):
                r = memory(); r['source_kind'] = kind; self.assertEqual(selected(r), [])

    def test_greeting_and_unrelated_topic_get_no_memory(self):
        self.assertEqual(selected(memory(), 'Hello, how are you?'), [])
        self.assertEqual(selected(memory(), 'Quantum optics'), [])

    def test_private_record_stays_excluded_from_public_query(self):
        self.assertEqual(selected(memory(), 'Publish my Tempe housing story'), [])

    def test_public_authorization_remains_required(self):
        r = memory(); r['privacy'] = 'owner_authorized_public'
        self.assertEqual(selected(r), [])
        r['publication_authorization'] = {'status': 'approved', 'granted_by': 'owner', 'scope': 'public_repository'}
        self.assertEqual(len(selected(r, 'Publish my Tempe housing story')), 1)

    def test_source_and_provenance_are_not_mutated(self):
        r = memory(); before = copy.deepcopy(r); selected(r); self.assertEqual(r, before)

    def test_existing_chat_type_needs_no_new_provenance_field(self):
        r = memory(); r['source_kind'] = 'owner_direct_chat_first_person_account'; r.pop('source_verification')
        self.assertEqual(len(selected(r)), 1)


if __name__ == '__main__':
    unittest.main()
