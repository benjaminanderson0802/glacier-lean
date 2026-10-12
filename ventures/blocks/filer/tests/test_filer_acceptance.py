import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from ventures.blocks.filer import prepare, submit


class PortalState:
    confirmations = 0


class MockPortal(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_html('<form method="post" action="/login"><input name="username"><input name="password" type="password"><button>Sign in</button></form>')
        elif self.path == "/step/1":
            self.send_html('<form method="post" action="/step/1"><input name="business_name"><input name="employee_count"><button>Continue</button></form>')
        elif self.path == "/step/2":
            self.send_html('<form method="post" action="/step/2"><input name="hours_worked"><button>Review</button></form>')
        elif self.path == "/review":
            self.send_html('<form method="post" action="/confirm"><p>Review filing</p><button>Submit filing</button></form>')
        elif self.path == "/confirmation":
            self.send_html('<main>Confirmation number: LOCAL-0001</main>')
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        if self.path == "/login":
            if form.get("username") == ["test-user"] and form.get("password") == ["test-password"]:
                self.send_response(302)
                self.send_header("Location", "/step/1")
                self.send_header("Set-Cookie", "session=local-test; Path=/")
                self.end_headers()
            else:
                self.send_error(401)
        elif self.path == "/step/1":
            self.send_response(302)
            self.send_header("Location", "/step/2")
            self.end_headers()
        elif self.path == "/step/2":
            self.send_response(302)
            self.send_header("Location", "/review")
            self.end_headers()
        elif self.path == "/confirm":
            PortalState.confirmations += 1
            self.send_response(302)
            self.send_header("Location", "/confirmation")
            self.end_headers()
        else:
            self.send_error(404)

    def send_html(self, content):
        body = f"<!doctype html><html><body>{content}</body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PortalFilerAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockPortal)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.portal_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        PortalState.confirmations = 0
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.auth = {"base_url": self.portal_url, "username": "test-user", "password": "test-password"}
        self.fields = {"business_name": "Example Works", "employee_count": "22", "hours_worked": "41200"}

    def test_prepare_fills_multistep_form_and_never_submits(self):
        draft = prepare("local-mock", self.fields, self.auth, evidence_dir=self.temp.name)
        self.assertTrue(Path(draft["screenshot"]).is_file())
        self.assertEqual(PortalState.confirmations, 0)
        self.assertTrue(draft["idempotency_key"])
        self.assertEqual(draft["status"], "prepared")

    def test_approved_submit_saves_confirmation_and_replay_does_not_double_file(self):
        draft = prepare("local-mock", self.fields, self.auth, evidence_dir=self.temp.name)
        confirmation = submit(draft, "owner-approval-17", evidence_dir=self.temp.name)
        replay = submit(draft, "owner-approval-17", evidence_dir=self.temp.name)
        self.assertEqual(PortalState.confirmations, 1)
        self.assertEqual(confirmation, replay)
        self.assertEqual(confirmation["status"], "submitted")
        self.assertIn("LOCAL-0001", confirmation["reference"])
        self.assertTrue(Path(confirmation["screenshot"]).is_file())
        self.assertTrue(Path(confirmation["pdf"]).is_file())

    def test_submit_requires_approval(self):
        draft = prepare("local-mock", self.fields, self.auth, evidence_dir=self.temp.name)
        with self.assertRaisesRegex(ValueError, "approval"):
            submit(draft, "", evidence_dir=self.temp.name)
        self.assertEqual(PortalState.confirmations, 0)


if __name__ == "__main__":
    unittest.main()
