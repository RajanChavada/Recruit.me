from __future__ import annotations

from app.db import Base, engine  # expects Base + engine to exist in app/db.py

# Ensure models are imported so they register with Base.metadata
import app.models  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema created (create_all).")


if __name__ == "__main__":
    main()