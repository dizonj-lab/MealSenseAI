"""Grant or revoke the admin role. Run on the server, never exposed through the API:

    docker compose exec backend python -m app.tools.admin grant joel.dizon@live.com
    docker compose exec backend python -m app.tools.admin revoke someone@example.com
    docker compose exec backend python -m app.tools.admin list

The account must already exist (sign up in the app first). Granting also marks the email as verified: whoever can
run this command on the server vouches for the address.
"""
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import User
from app.services import audit


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("grant", "revoke", "list") or (argv[0] != "list" and len(argv) != 2):
        print(__doc__)
        return 2
    with SessionLocal() as db:
        if argv[0] == "list":
            for u in db.scalars(select(User).where(User.is_admin).order_by(User.id)):
                print(f"{u.id}\t{u.email}")
            return 0
        user = db.scalar(select(User).where(User.email == argv[1].strip().lower()))
        if not user:
            print(f"No account for {argv[1]}. Sign up in the app first, then run this again.")
            return 1
        user.is_admin = argv[0] == "grant"
        if user.is_admin and not user.email_verified_at:
            user.email_verified_at = datetime.now(timezone.utc)
        audit.log(db, None, f"admin.{argv[0]}", "user", user.id, email=user.email, via="server command")
        db.commit()
        print(f"{user.email}: admin {'granted' if user.is_admin else 'revoked'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
