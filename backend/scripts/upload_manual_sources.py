#!/usr/bin/env python3
"""Upload diagnostic panels and literature data with new thresholds."""

from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"


def get_token():
    """Get authentication token."""
    response = httpx.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def upload_file(token: str, source: str, file_path: Path):
    """Upload a single file."""
    headers = {"Authorization": f"Bearer {token}"}

    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "application/json")}
        data = {"mode": "full"}

        response = httpx.post(
            f"{BASE_URL}/api/ingestion/{source}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            genes = result.get("data", {}).get("genes_processed", 0)
            print(f"  ✅ {file_path.name}: {genes} genes")
        else:
            print(f"  ❌ {file_path.name}: {response.status_code} - {response.text}")


def main():
    """Main upload function."""
    print("🔐 Getting authentication token...")
    token = get_token()
    print("✅ Token obtained\n")

    # Upload diagnostic panels
    panels_dir = Path("/home/bernt-popp/development/kidney-genetics-db/scrapers/diagnostics/output/2025-08-24")
    if panels_dir.exists():
        print("📦 Uploading Diagnostic Panels...")
        for file_path in sorted(panels_dir.glob("*.json")):
            upload_file(token, "DiagnosticPanels", file_path)
        print()

    # Upload literature
    lit_dir = Path("/home/bernt-popp/development/kidney-genetics-db/scrapers/literature/output/2025-08-24")
    if lit_dir.exists():
        print("📚 Uploading Literature...")
        for file_path in sorted(lit_dir.glob("literature_pmid_*.json")):
            upload_file(token, "Literature", file_path)
        print()

    print("✨ Upload complete!")


if __name__ == "__main__":
    main()
