"""Developer-only CLI; never expose this operation as a public endpoint."""

import argparse
import time
import jwt
from app.config import Settings
from app.db import Database


def issue(user, settings):
    return jwt.encode(
        {
            "sub": user,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("user", choices=["user_1", "user_2", "user_3", "admin"])
    args = parser.parse_args()
    s = Settings()
    s.validate_runtime()
    db = Database(s.database_url)
    db.seed()
    print(issue(args.user, s))
