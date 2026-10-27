import unittest
from uuid import uuid4

from app import security
from app.errors import AppError


class MediaTokenTests(unittest.TestCase):
    def test_round_trip(self):
        accident = uuid4()
        token, expires = security.sign_media(accident, "masked", ttl=60, now=1000)
        self.assertEqual(expires, 1060)
        self.assertEqual(security.verify_media(token, now=1030), (accident, "masked"))

    def test_expired_token_is_rejected(self):
        token, _ = security.sign_media(uuid4(), "masked", ttl=60, now=1000)
        with self.assertRaises(AppError) as ctx:
            security.verify_media(token, now=1061)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_tampered_token_is_rejected(self):
        accident = uuid4()
        token, _ = security.sign_media(accident, "masked", ttl=60, now=1000)
        for bad in (token.replace("masked", "original"), token[:-1] + ("0" if token[-1] != "0" else "1"),
                    token.replace(str(accident), str(uuid4())), "garbage", ""):
            with self.assertRaises(AppError):
                security.verify_media(bad, now=1010)


if __name__ == "__main__":
    unittest.main()
