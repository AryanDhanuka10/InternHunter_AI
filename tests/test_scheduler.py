"""
Day 7 — Scheduler Tests
Run:  pytest tests/test_scheduler.py -v
      pytest tests/ -v
"""
import sys, os
import unittest.mock as mock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────

def _fake_opp(n: int) -> dict:
    return {
        "title":      f"Intern #{n}",
        "role":       "ml intern",
        "company":    "TestCo",
        "link":       f"https://example.com/{n}",
        "source":     "internshala.com",
        "stipend":    "₹15,000/month",
        "deadline":   "31 May 2025",
        "location":   "Remote",
        "apply_link": f"https://example.com/{n}",
        "snippet":    "test snippet",
        "scraped_at": "2025-04-26T00:00:00",
        "parsed":     True,
        "id":         n,
    }


def _patch_all(scrape_returns=None, send_returns=True):
    """Return a dict of all patches needed to run scheduler without real I/O."""
    opps = scrape_returns or [_fake_opp(i) for i in range(3)]
    return {
        "scrape_all_roles":      mock.Mock(return_value=opps),
        "parse_all":             mock.Mock(return_value=opps),
        "init_db":               mock.Mock(),
        "upsert_many":           mock.Mock(return_value=(3, 0)),
        "get_new_opportunities": mock.Mock(return_value=opps),
        "get_stats":             mock.Mock(return_value={"total":3,"new":3,"applied":0,"with_stipend":3,"with_deadline":3,"with_location":3,"notified":0}),
        "build_digest_html":     mock.Mock(return_value="<html>test</html>"),
        "build_digest_text":     mock.Mock(return_value="plain text"),
        "save_digest":           mock.Mock(return_value=("data/digest/test.html","data/digest/test.txt")),
        "send_digest_email":     mock.Mock(return_value=send_returns),
        "mark_notified":         mock.Mock(),
        "apply_filters":          mock.Mock(return_value=([_fake_opp(i) for i in range(3)], [])),
    }


# ════════════════════════════════════════════════════════
#  run() happy path
# ════════════════════════════════════════════════════════

class TestSchedulerRun:

    def test_returns_summary_dict(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()
        assert isinstance(summary, dict)

    def test_summary_has_required_keys(self):
        from internhunter.scheduler import run
        with mock.patch.multiple("internhunter.scheduler", **_patch_all()):
            summary = run()
        for key in ("scraped","parsed","inserted","duplicates",
                    "new_opps","email_sent","stages_ok","stages_fail","elapsed_s"):
            assert key in summary, f"Missing key: {key}"

    def test_all_stages_succeed(self):
        from internhunter.scheduler import run
        with mock.patch.multiple("internhunter.scheduler", **_patch_all()):
            summary = run()
        assert summary["stages_fail"] == []
        assert len(summary["stages_ok"]) == 7   # db_init, scrape, parse, filter, store, digest, notify

    def test_scraped_count_in_summary(self):
        from internhunter.scheduler import run
        opps = [_fake_opp(i) for i in range(7)]
        patches = _patch_all(scrape_returns=opps)
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()
        assert summary["scraped"] == 7

    def test_email_sent_true_when_send_succeeds(self):
        from internhunter.scheduler import run
        with mock.patch.multiple("internhunter.scheduler", **_patch_all(send_returns=True)):
            summary = run()
        assert summary["email_sent"] is True

    def test_email_sent_false_when_send_fails(self):
        from internhunter.scheduler import run
        with mock.patch.multiple("internhunter.scheduler", **_patch_all(send_returns=False)):
            summary = run()
        assert summary["email_sent"] is False

    def test_mark_notified_called_when_email_sent(self):
        from internhunter.scheduler import run
        patches = _patch_all(send_returns=True)
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["mark_notified"].assert_called_once()

    def test_mark_notified_not_called_when_email_fails(self):
        from internhunter.scheduler import run
        patches = _patch_all(send_returns=False)
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["mark_notified"].assert_not_called()

    def test_elapsed_time_is_positive(self):
        from internhunter.scheduler import run
        with mock.patch.multiple("internhunter.scheduler", **_patch_all()):
            summary = run()
        assert summary["elapsed_s"] >= 0

    def test_no_notify_when_no_new_opps(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        patches["get_new_opportunities"] = mock.Mock(return_value=[])
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()
        assert summary["new_opps"] == 0
        patches["send_digest_email"].assert_not_called()


# ════════════════════════════════════════════════════════
#  Stage error isolation
# ════════════════════════════════════════════════════════

class TestStageIsolation:

    def test_scrape_failure_does_not_crash_pipeline(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        patches["scrape_all_roles"] = mock.Mock(
            side_effect=Exception("Serper down")
        )
        patches["parse_all"] = mock.Mock(return_value=[])
        patches["upsert_many"] = mock.Mock(return_value=(0,0))
        patches["get_new_opportunities"] = mock.Mock(return_value=[])
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()   # must not raise
        assert "scrape" in summary["stages_fail"]

    def test_send_failure_does_not_crash_pipeline(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        patches["send_digest_email"] = mock.Mock(
            side_effect=Exception("SMTP gone")
        )
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()   # must not raise
        assert "notify" in summary["stages_fail"]

    def test_store_failure_recorded_in_summary(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        patches["upsert_many"] = mock.Mock(
            side_effect=Exception("DB locked")
        )
        patches["get_new_opportunities"] = mock.Mock(return_value=[])
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()
        assert "store" in summary["stages_fail"]

    def test_stages_ok_list_excludes_failed_stage(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        patches["scrape_all_roles"] = mock.Mock(
            side_effect=Exception("network error")
        )
        patches["parse_all"] = mock.Mock(return_value=[])
        patches["upsert_many"] = mock.Mock(return_value=(0,0))
        patches["get_new_opportunities"] = mock.Mock(return_value=[])
        with mock.patch.multiple("internhunter.scheduler", **patches):
            summary = run()
        assert "scrape" not in [s.lower() for s in summary["stages_ok"]]


# ════════════════════════════════════════════════════════
#  Stage ordering — verify each module is called
# ════════════════════════════════════════════════════════

class TestStageOrdering:
    """Verify each stage function is actually called during a run."""

    def test_init_db_called(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["init_db"].assert_called_once()

    def test_scrape_called(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["scrape_all_roles"].assert_called_once()

    def test_parse_called_with_scraped_output(self):
        from internhunter.scheduler import run
        opps    = [_fake_opp(1)]
        patches = _patch_all(scrape_returns=opps)
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["parse_all"].assert_called_once_with(opps)

    def test_upsert_many_called(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["upsert_many"].assert_called_once()

    def test_build_digest_html_called_when_opps_exist(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["build_digest_html"].assert_called_once()

    def test_send_digest_email_called_when_opps_exist(self):
        from internhunter.scheduler import run
        patches = _patch_all()
        with mock.patch.multiple("internhunter.scheduler", **patches):
            run()
        patches["send_digest_email"].assert_called_once()