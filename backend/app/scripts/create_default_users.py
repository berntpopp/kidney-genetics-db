#!/usr/bin/env python3
"""
Script to create default users for the Kidney Genetics Database.
Run this after database migration to set up initial admin and optionally curator accounts.
"""

import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User


def create_default_users():
    """Create default admin and optionally curator users."""
    db = SessionLocal()

    try:
        # Check if admin already exists
        result = db.execute(
            select(User).where(
                (User.username == settings.ADMIN_USERNAME) |
                (User.email == settings.ADMIN_EMAIL)
            )
        )
        admin = result.scalar_one_or_none()

        if admin:
            print(f"Admin user already exists: {admin.username} ({admin.email})")
            # Update admin password if different
            if not admin.role == "admin":
                admin.role = "admin"
                admin.is_admin = True
                db.commit()
                print(f"Updated {admin.username} to admin role")
        else:
            # Create admin user
            admin = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="System Administrator",
                role="admin",
                is_admin=True,
                is_active=True,
                is_verified=True,
                failed_login_attempts=0
            )
            db.add(admin)
            db.commit()
            print(f"Created admin user: {settings.ADMIN_USERNAME}")
            print(f"  Email: {settings.ADMIN_EMAIL}")
            print(f"  Password: {settings.ADMIN_PASSWORD}")
            print("  ⚠️  IMPORTANT: Change the admin password immediately after first login!")

        # Optionally create a test curator
        if hasattr(settings, 'CURATOR_USERNAME'):
            result = db.execute(
                select(User).where(User.username == settings.CURATOR_USERNAME)
            )
            curator = result.scalar_one_or_none()

            if curator:
                print(f"Curator user already exists: {curator.username}")
            else:
                curator = User(
                    email=getattr(settings, 'CURATOR_EMAIL', 'curator@kidney-genetics.local'),
                    username=settings.CURATOR_USERNAME,
                    hashed_password=get_password_hash(
                        getattr(settings, 'CURATOR_PASSWORD', 'ChangeMe!Curator2024')
                    ),
                    full_name="Test Curator",
                    role="curator",
                    is_admin=False,
                    is_active=True,
                    is_verified=True,
                    failed_login_attempts=0
                )
                db.add(curator)
                db.commit()
                print(f"Created curator user: {curator.username}")

        print("\n✅ Default users created successfully!")
        print("\n📝 Notes:")
        print("- The database is PUBLIC - all data is readable without authentication")
        print("- Authentication is only required for data modification")
        print("- Admins can create additional curator accounts via the API")
        print("- Remember to change default passwords in production!")

    except Exception as e:
        print(f"❌ Error creating users: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_default_users()
