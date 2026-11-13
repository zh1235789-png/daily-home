# python3 build/test_dismiss_mail.py
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import mail_id, mail_thread  # noqa: E402
from dismiss_mail import dismiss  # noqa: E402

U1 = "https://mail.google.com/mail/?authuser=x#all/thread-f:111"
U2 = "https://mail.google.com/mail/?authuser=x#all/thread-f:222"
G = {"updated": "u", "items": [{"from": "A", "subject": "件名1", "url": U1}, {"from": "B", "subject": "件名2", "url": U2}]}


class T(unittest.TestCase):
    def test_thread(self):
        self.assertEqual(mail_thread(U1), "111")
        self.assertEqual(mail_thread("https://x"), "")
        self.assertEqual(mail_id("https://x"), "")
        self.assertRegex(mail_id(U1), r"^[0-9a-f]{10}$")

    def test_dismiss_one(self):
        g, d, done = dismiss(G, {"threads": []}, [mail_id(U1)], "2026-11-13")
        self.assertEqual([x["subject"] for x in g["items"]], ["件名2"])
        self.assertEqual(d["threads"][0]["thread"], "111")
        self.assertEqual(d["threads"][0]["subject"], "件名1")
        self.assertEqual(len(done), 1)
        self.assertEqual(g["updated"], "u")

    def test_keeps_existing_and_no_dup(self):
        d0 = {"threads": [{"thread": "111", "note": "前から"}]}
        g, d, done = dismiss(G, d0, [mail_id(U1)], "2026-11-13")
        self.assertEqual(len(d["threads"]), 1)
        self.assertEqual(d["threads"][0]["note"], "前から")

    def test_unknown_id(self):
        g, d, done = dismiss(G, None, ["0123456789"], "2026-11-13")
        self.assertEqual(len(g["items"]), 2)
        self.assertEqual(done, [])
        self.assertEqual(d["threads"], [])


if __name__ == "__main__":
    unittest.main()
