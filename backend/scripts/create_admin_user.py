#!/usr/bin/env python
"""
Create admin user script using configuration values.
This script ensures consistent admin user creation across the application.
"""

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
    """Create an admin user using configuration values."""
    # Create database engine
    engine = create_engine(settings.DATABASE_URL.get_secret_value())
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    db = SessionLocal()

    try:
        # Check if admin user already exists (check both username and email)
        existing_admin = (
            db.query(User)
            .filter(
                (User.username == settings.ADMIN_USERNAME) | (User.email == settings.ADMIN_EMAIL)
            )
            .first()
        )

        if existing_admin:
            print("✓ Admin user already exists!")
            # Update to ensure correct settings from config, including password
            existing_admin.username = settings.ADMIN_USERNAME
            existing_admin.email = settings.ADMIN_EMAIL
            existing_admin.hashed_password = get_password_hash(
                settings.ADMIN_PASSWORD.get_secret_value()
            )  # Update password too!
            existing_admin.role = "admin"
            existing_admin.is_active = True
            existing_admin.is_verified = True
            existing_admin.is_admin = True
            db.commit()
            print("✓ Updated admin user settings to match config (including password)")
            return

        # Create admin user using config values
        admin_user = User(
            email=settings.ADMIN_EMAIL,
            username=settings.ADMIN_USERNAME,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD.get_secret_value()),
            full_name="Administrator",
            role="admin",
            is_active=True,
            is_verified=True,
            is_admin=True,
        )

        db.add(admin_user)
        db.commit()

        print("✅ Admin user created successfully!")
        print(f"📧 Email: {settings.ADMIN_EMAIL}")
        print(f"👤 Username: {settings.ADMIN_USERNAME}")
        print("🔑 Password: ********** (as configured in ADMIN_PASSWORD env var)")
        print("⚠️  Please change this password after first login!")
        print("\n📝 Note: These credentials are defined in app/core/config.py")

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
