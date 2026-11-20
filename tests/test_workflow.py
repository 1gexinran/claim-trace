import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace

import claimtrace as ct
from test_benchmark import PAIR


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.items = ct.prepare([PAIR], 2)
        self.oracle = {r["id"]: {"id": r["id"], "response": {
            "choice": r["answer"], "evidence": r["evidence"][0]}} for r in self.items}

    def test_missing_duplicate_or_foreign_rows_fail(self):
        with self.assertRaises(ValueError):
            ct.summarize(self.items, {})
        with self.assertRaises(ValueError):
            ct.summarize(self.items, {**self.oracle, "other": {}})
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "responses"
            line = json.dumps(next(iter(self.oracle.values()))) + "\n"
            f.write_text(line * 2)
            with self.assertRaises(ValueError):
                ct.read_rows(f)

    def test_mixed_models_and_stale_key_rejected(self):
        rows = {k: dict(r, config={"model": "one", "bank": ct.digest(self.items)}, served_model="one")
                for k, r in self.oracle.items()}
        one_row = next(iter(rows.values()))
        one_row["served_model"] = "another"
        with self.assertRaises(ValueError):
            ct.summarize(self.items, rows)
        one_row["served_model"] = "one"
        for row in rows.values():
            row["config"]["bank"] = "other-revision"
        with self.assertRaises(ValueError):
            ct.summarize(self.items, rows)

    def test_calibration_requires_two_and_preserves_matches(self):
        perfect = ct.summarize(self.items, self.oracle)
        mixed = self.oracle.copy()
        mixed[self.items[0]["id"]] = dict(response="unparseable")
        partial = ct.summarize(self.items, mixed)
        with self.assertRaises(ValueError):
            ct.calibrate(self.items, {"only": perfect})
        report = ct.calibrate(self.items, {"good": perfect, "bad": partial})
        self.assertEqual(report["pair_bands"], {"split": 1})
        self.assertEqual(report["scores"]["bad"]["overall"]["evidence_score"], 0.5)
        self.assertEqual(report["contrasts"][0]["evidence_delta_pp"], 50)
        self.assertEqual(report["evidence_pairs"]["p"]["spread"], 0.5)
        self.assertEqual(report["scores"]["bad"]["overall"]["invalid"], 1)
        self.assertEqual(report["scores"]["bad"]["overall"]["grounded"], 1)
        self.assertEqual(report["contrasts"][0]["a_only"], 1)
        self.assertEqual(report["contrasts"][0]["delta_pp"], 100)
        self.assertEqual(ct.calibrate(self.items, {"a": perfect, "b": perfect})["pair_bands"], {"ceiling": 1})
        self.assertEqual(ct.calibrate(self.items, {"a": partial, "b": partial})["pair_bands"], {"floor": 1})

    def test_http_run_sends_one_packet_and_resumes(self):
        received = []
        class Server(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                received.append(body)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"choices":[{"message":{"content":"example"}}],"model":"test"}')
            def log_message(self, *args):
                pass
        with HTTPServer(("127.0.0.1", 0), Server) as service, tempfile.TemporaryDirectory() as tmp:
            thread = threading.Thread(target=service.serve_forever, daemon=True)
            thread.start()
            try:
                args = SimpleNamespace(output=Path(tmp) / "run.jsonl", key_env=None, model="mock",
                                       base_url="http://127.0.0.1:%d/v1" % service.server_port,
                                       seed=2, temperature=0, timeout=5, structured=True)
                ct.administer(self.items, args)
                complete = args.output.read_bytes()
                first = complete.splitlines()[0]
                args.output.write_bytes(first)
                ct.administer(self.items, args)
                self.assertEqual(len(ct.read_rows(args.output)), 2)
                args.output.write_bytes(first + b'\n{"id":"partial')
                ct.administer(self.items, args)
                ct.administer(self.items, args)
                self.assertEqual(len(received), 4)
                self.assertEqual(received[0]["messages"], [{"role":"user", "content": self.items[0]["prompt"]}])
                self.assertEqual(set(ct.read_rows(args.output)), set(self.oracle))
                args.model = "different"
                with self.assertRaises(ValueError):
                    ct.administer(self.items, args)
            finally:
                service.shutdown()
                thread.join()
