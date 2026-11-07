from __future__ import annotations

import unittest

import httpx
from fastapi.testclient import TestClient

from .app import app, _exact_mcnemar, _wilson


class WebApiTests(unittest.TestCase):
    def test_statistics_helpers(self):
        lo, hi = _wilson(50, 100)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        self.assertEqual(_exact_mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(_exact_mcnemar(0, 4), 0.125)

    def test_health_and_replay_are_real_saved_evidence(self):
        client = TestClient(app)
        health = client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ready")
        replay = client.get("/api/research")
        self.assertEqual(replay.status_code, 200)
        body = replay.json()
        self.assertEqual(body["mode"], "saved_replay")
        self.assertEqual(body["audit"], "PASS")
        self.assertFalse(body["independent_test_accessed"])
        self.assertEqual(body["aggregate"]["paired_evaluation_shots"], 87500)

    def test_real_paired_stim_pymatching_simulation(self):
        client = TestClient(app)
        response = client.post("/api/simulate", json={
            "burst_probability": 0.006,
            "shots": 100,
            "calibration_shots": 500,
            "seed": 123,
        })
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["mode"], "live_simulation")
        self.assertEqual(data["evaluation_shots"], 100)
        self.assertTrue(data["paired_evaluation"])
        self.assertEqual(len(data["methods"]), 3)
        self.assertEqual([m["id"] for m in data["methods"]], [
            "fixed_nominal", "detector_estimated", "privileged_reference"
        ])
        self.assertEqual(len(data["records"]), 12)
        self.assertEqual(len(data["records"][0]["detectors"]), 40)
        self.assertEqual(len(data["records"][0]["detector_slices"]), 6)
        ids = [detector_id for row in data["records"][0]["detector_slices"] for detector_id in row["detector_ids"]]
        self.assertEqual(sorted(ids), list(range(40)))
        self.assertEqual(data["software"]["stim"], "1.16.0")
        self.assertNotIn("independent_test", data)

    def test_shot_cap_is_enforced(self):
        response = TestClient(app).post("/api/simulate", json={
            "burst_probability": 0.0, "shots": 10001, "calibration_shots": 500, "seed": 3
        })
        self.assertEqual(response.status_code, 422)


class LocalhostGuardTests(unittest.IsolatedAsyncioTestCase):
    async def request_from(self, client_host: str, forwarded_for: str | None = None):
        transport = httpx.ASGITransport(app=app, client=(client_host, 54321))
        headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/api/health", headers=headers)

    async def test_ipv4_and_ipv6_loopback_are_allowed(self):
        for address in ("127.0.0.1", "::1"):
            response = await self.request_from(address)
            self.assertEqual(response.status_code, 200, address)

    async def test_remote_and_spoofed_forwarded_headers_are_rejected(self):
        response = await self.request_from("203.0.113.8", "127.0.0.1")
        self.assertEqual(response.status_code, 403)
        self.assertIn("localhost", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
