"""Independent assertions on the synthetic reference path and on its receivers."""
import unittest

from provider_probe import Receiver, scenario


class BoundaryTests(unittest.TestCase):
    def test_denied_profile_stops_before_fixture_read(self):
        item = scenario("changed_endpoint")
        self.assertEqual(item["events"], ["reply"])
        self.assertEqual(item["reason"], "UNAPPROVED_PROFILE")
        self.assertFalse(item["client_contains_marker"])
        self.assertEqual(item["fallback"]["post_requests"], 0)

    def test_nonempty_fragment_is_counted_even_without_marker(self):
        events = []
        receiver = Receiver("test", b"unique-marker", b"full-result", events)
        receiver.handle("/model", b"full")
        self.assertEqual(receiver.counts(), {"post_requests": 1, "nonempty_bodies": 1,
                                             "with_marker": 0, "exact_result": 0})

    def test_outage_observed_at_primary_and_fallback_remains_unused(self):
        item = scenario("primary_unavailable")
        self.assertEqual(item["events"], ["read", "reply", "primary"])
        self.assertEqual(item["reason"], "PRIMARY_UNAVAILABLE")
        self.assertEqual(item["primary"]["exact_result"], 1)
        self.assertEqual(item["fallback"]["post_requests"], 0)

    def test_invalid_snapshot_never_reaches_client_or_provider(self):
        item = scenario("incomplete")
        self.assertEqual(item["source_reads"], 1)
        self.assertEqual(item["reason"], "INVALID_RESULT")
        self.assertTrue(item["checks"]["client_received_exact_allowed_reply"])
        self.assertEqual(item["primary"]["nonempty_bodies"], 0)
