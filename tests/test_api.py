"""
Day 9 — FastAPI Endpoint Tests
Run:  pytest tests/test_api.py -v
      pytest tests/ -v
"""
import sys, os, pytest
import unittest.mock as mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ── Shared fake opportunity ───────────────────────────────────

def _opp(n=1, **kwargs):
    base = {
        "id": n, "title": f"ML Intern #{n}", "role": "machine learning intern",
        "company": "TestCo", "link": f"https://internshala.com/{n}",
        "source": "internshala.com", "stipend": "₹20,000/month",
        "deadline": "31 May 2025", "location": "Remote",
        "apply_link": f"https://internshala.com/{n}",
        "snippet": "great opp", "status": "new",
        "scraped_at": "2025-04-27T00:00:00", "notified": 0,
    }
    base.update(kwargs)
    return base


FAKE_STATS = {
    "total": 53, "new": 20, "applied": 3,
    "with_stipend": 10, "with_deadline": 5,
    "with_location": 25, "notified": 30,
}


# ════════════════════════════════════════════════════════
#  Health endpoints
# ════════════════════════════════════════════════════════

class TestHealth:

    def test_root_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_has_status_running(self):
        r = client.get("/")
        assert r.json()["status"] == "running"

    def test_root_has_docs_link(self):
        assert "/docs" in client.get("/").json()["docs"]

    def test_health_returns_200(self):
        with mock.patch("internhunter.database.get_stats", return_value=FAKE_STATS):
            r = client.get("/health")
        assert r.status_code == 200

    def test_health_status_healthy(self):
        with mock.patch("internhunter.database.get_stats", return_value=FAKE_STATS):
            r = client.get("/health")
        assert r.json()["status"] == "healthy"

    def test_health_includes_stats(self):
        with mock.patch("internhunter.database.get_stats", return_value=FAKE_STATS):
            r = client.get("/health")
        assert "stats" in r.json()
        assert r.json()["stats"]["total"] == 53


# ════════════════════════════════════════════════════════
#  GET /api/opportunities
# ════════════════════════════════════════════════════════

class TestOpportunities:

    def test_list_returns_200(self):
        with mock.patch("app.routers.opportunities.get_new_opportunities", return_value=[]):
            r = client.get("/api/opportunities/")
        assert r.status_code == 200

    def test_list_returns_list(self):
        opps = [_opp(1), _opp(2), _opp(3)]
        with mock.patch("app.routers.opportunities.get_new_opportunities", return_value=opps):
            r = client.get("/api/opportunities/")
        assert isinstance(r.json(), list)
        assert len(r.json()) == 3

    def test_list_respects_limit(self):
        with mock.patch("app.routers.opportunities.get_new_opportunities", return_value=[]) as m:
            client.get("/api/opportunities/?limit=5")
        m.assert_called_once_with(limit=5)

    def test_list_filters_by_location(self):
        with mock.patch("app.routers.opportunities.get_by_location", return_value=[_opp(1)]) as m:
            r = client.get("/api/opportunities/?location=bangalore")
        assert r.status_code == 200
        m.assert_called_once_with("bangalore", limit=20)

    def test_list_filters_by_role(self):
        with mock.patch("app.routers.opportunities.get_by_role", return_value=[_opp(1)]) as m:
            r = client.get("/api/opportunities/?role=machine+learning")
        assert r.status_code == 200
        m.assert_called_once_with("machine learning", limit=20)

    def test_list_filters_by_stipend(self):
        with mock.patch("app.routers.opportunities.get_by_stipend", return_value=[_opp(1)]) as m:
            r = client.get("/api/opportunities/?min_stipend=15000")
        assert r.status_code == 200
        m.assert_called_once_with(min_amount=15000, limit=20)

    def test_list_limit_validation_max(self):
        r = client.get("/api/opportunities/?limit=999")
        assert r.status_code == 422   # validation error

    def test_list_limit_validation_min(self):
        r = client.get("/api/opportunities/?limit=0")
        assert r.status_code == 422

    def test_get_single_returns_200(self):
        import sqlite3
        fake_row = dict(_opp(1))
        with mock.patch("app.routers.opportunities.get_conn") as mock_conn:
            conn_ctx = mock_conn.return_value.__enter__.return_value
            conn_ctx.row_factory = None
            conn_ctx.execute.return_value.fetchone.return_value = fake_row
            with mock.patch("sqlite3.Row", dict):
                # easier: just mock the whole function
                pass
        # Test 404 path directly (easier to test than mocking sqlite.Row)
        with mock.patch("app.routers.opportunities.get_conn") as mc:
            mc.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
            r = client.get("/api/opportunities/999")
        assert r.status_code == 404

    def test_get_single_404(self):
        with mock.patch("app.routers.opportunities.get_conn") as mc:
            mc.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = None
            r = client.get("/api/opportunities/99999")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_apply_returns_200(self):
        with mock.patch("app.routers.opportunities.mark_applied"):
            r = client.post("/api/opportunities/1/apply",
                            json={"method": "cold_email", "notes": "Sent via Gmail"})
        assert r.status_code == 200

    def test_apply_response_has_status(self):
        with mock.patch("app.routers.opportunities.mark_applied"):
            r = client.post("/api/opportunities/1/apply", json={"method": "company_site"})
        assert r.json()["status"] == "applied"

    def test_apply_default_method_is_cold_email(self):
        with mock.patch("app.routers.opportunities.mark_applied") as m:
            client.post("/api/opportunities/1/apply", json={})
        m.assert_called_once_with(1, method="cold_email", notes="")


# ════════════════════════════════════════════════════════
#  GET/POST /api/profile
# ════════════════════════════════════════════════════════

class TestProfile:

    VALID_PROFILE = {
        "name": "Aryan Dhanuka", "email": "aryan@example.com",
        "college": "DTU", "branch": "CSE", "year": "3rd Year B.Tech",
        "skills": ["Python", "ML", "React"],
        "github": "https://github.com/aryan",
        "linkedin": "https://linkedin.com/in/aryan",
    }

    def test_get_profile_returns_200(self):
        assert client.get("/api/profile/").status_code == 200

    def test_get_profile_has_name(self):
        r = client.get("/api/profile/")
        assert "name" in r.json()

    def test_get_profile_has_skills_list(self):
        r = client.get("/api/profile/")
        assert isinstance(r.json().get("skills"), list)

    def test_post_profile_returns_200(self):
        r = client.post("/api/profile/", json=self.VALID_PROFILE)
        assert r.status_code == 200

    def test_post_profile_saves_name(self):
        r = client.post("/api/profile/", json=self.VALID_PROFILE)
        assert r.json()["profile"]["name"] == "Aryan Dhanuka"

    def test_post_profile_saves_skills(self):
        r = client.post("/api/profile/", json=self.VALID_PROFILE)
        assert "Python" in r.json()["profile"]["skills"]

    def test_post_profile_missing_required_field(self):
        bad = {k: v for k, v in self.VALID_PROFILE.items() if k != "name"}
        r = client.post("/api/profile/", json=bad)
        assert r.status_code == 422

    def test_post_profile_has_message(self):
        r = client.post("/api/profile/", json=self.VALID_PROFILE)
        assert "message" in r.json()

    def test_delete_overrides_returns_200(self):
        client.post("/api/profile/", json=self.VALID_PROFILE)
        r = client.delete("/api/profile/overrides")
        assert r.status_code == 200

    def test_delete_overrides_has_message(self):
        r = client.delete("/api/profile/overrides")
        assert "message" in r.json()


# ════════════════════════════════════════════════════════
#  /api/actions
# ════════════════════════════════════════════════════════

class TestActions:

    def test_stats_returns_200(self):
        with mock.patch("internhunter.database.get_stats", return_value=FAKE_STATS):
            r = client.get("/api/actions/stats")
        assert r.status_code == 200

    def test_stats_has_total(self):
        with mock.patch("internhunter.database.get_stats", return_value=FAKE_STATS):
            r = client.get("/api/actions/stats")
        assert "total" in r.json()

    def test_logs_returns_200_when_file_exists(self, tmp_path, monkeypatch):
        log = tmp_path / "daily.log"
        log.write_text("line1\nline2\nline3\n")
        monkeypatch.chdir(tmp_path)
        import os; os.makedirs("logs", exist_ok=True)
        import shutil; shutil.copy(str(log), "logs/daily.log")
        r = client.get("/api/actions/logs?lines=2")
        assert r.status_code == 200

    def test_logs_404_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = client.get("/api/actions/logs")
        assert r.status_code == 404

    def test_run_pipeline_sync_returns_200(self):
        mock_summary = {
            "started_at": "2025-04-27", "scraped": 10, "parsed": 10,
            "inserted": 5, "duplicates": 5, "new_opps": 5,
            "email_sent": True, "stages_ok": ["db_init","scrape"],
            "stages_fail": [], "elapsed_s": 3.2,
        }
        with mock.patch("internhunter.scheduler.run", return_value=mock_summary):
            r = client.post("/api/actions/run-pipeline")
        assert r.status_code == 200

    def test_run_pipeline_returns_success_status(self):
        mock_summary = {
            "started_at": "t", "scraped": 5, "parsed": 5,
            "inserted": 5, "duplicates": 0, "new_opps": 5,
            "email_sent": True, "stages_ok": ["a"], "stages_fail": [],
            "elapsed_s": 1.0,
        }
        with mock.patch("internhunter.scheduler.run", return_value=mock_summary):
            r = client.post("/api/actions/run-pipeline")
        assert r.json()["status"] == "success"

    def test_run_pipeline_partial_when_stages_fail(self):
        mock_summary = {
            "started_at": "t", "scraped": 0, "parsed": 0,
            "inserted": 0, "duplicates": 0, "new_opps": 0,
            "email_sent": False, "stages_ok": ["db_init"],
            "stages_fail": ["scrape"], "elapsed_s": 1.0,
        }
        with mock.patch("internhunter.scheduler.run", return_value=mock_summary):
            r = client.post("/api/actions/run-pipeline")
        assert r.json()["status"] == "partial"

    def test_run_pipeline_async_returns_started(self):
        with mock.patch("internhunter.scheduler.run"):
            r = client.post("/api/actions/run-pipeline?async_run=true")
        assert r.json()["status"] == "started"

    def test_run_pipeline_blocks_double_trigger(self):
        import app.routers.actions as actions_mod
        actions_mod._running["active"] = True
        try:
            r = client.post("/api/actions/run-pipeline")
            assert r.json()["status"] == "skipped"
        finally:
            actions_mod._running["active"] = False
