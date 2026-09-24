"""Creates local-only secrets. Does not contact any external service."""

import secrets
from app.config import ROOT

if __name__ == "__main__":
    p = ROOT / ".env"
    if p.exists():
        print(".env already exists; leaving it unchanged.")
    else:
        p.write_text(
            (ROOT / ".env.example")
            .read_text()
            .replace("CHANGE_ME_TO_A_RANDOM_32_PLUS_CHARACTER_SECRET", secrets.token_urlsafe(48))
            .replace("CHANGE_ME_DATABASE_PASSWORD", secrets.token_urlsafe(24))
        )
        try:
            p.chmod(0o600)
        except OSError:
            pass
        print("Created .env. Keep it private. Next: python -m scripts.issue_token user_1")
    (ROOT / "runtime").mkdir(exist_ok=True)
