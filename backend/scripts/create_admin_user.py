#!/usr/bin/env python
"""Create an admin user for the Kidney Genetics Database."""

import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User


def create_admin_user():
    """Create an admin user."""
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.email == "admin@kidneygenetics.org").first()

        if existing_admin:
            print("Admin user already exists!")
            return

        # Create admin user
        admin_user = User(
            email="admin@kidneygenetics.org",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )

        db.add(admin_user)
        db.commit()

        print("✅ Admin user created successfully!")
        print("📧 Email: admin@kidneygenetics.org")
        print("🔑 Password: admin123")
        print("⚠️  Please change this password after first login!")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
