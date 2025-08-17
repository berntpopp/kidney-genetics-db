#!/usr/bin/env python3
"""Remove OMIM from database."""

from app.core.database import SessionLocal
from app.models.progress import DataSourceProgress


def remove_omim():
    db = SessionLocal()
    try:
        # Remove OMIM progress record
        omim = db.query(DataSourceProgress).filter(
            DataSourceProgress.source_name == "OMIM"
        ).first()

        if omim:
            db.delete(omim)
            db.commit()
            print("✅ Removed OMIM from database")
        else:
            print("ℹ️ OMIM not found in database")

    finally:
        db.close()

if __name__ == "__main__":
    remove_omim()
