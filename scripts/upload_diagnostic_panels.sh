#!/bin/bash
# Upload diagnostic panels to the kidney-genetics database
# Each provider must be uploaded separately to preserve source attribution for evidence counting

TOKEN="$1"
if [ -z "$TOKEN" ]; then
    echo "Getting auth token..."
    TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=admin&password=ChangeMe!Admin2024")
    TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
fi

PANELS_DIR="scrapers/diagnostics/output/2025-08-24"

echo "Uploading diagnostic panels from $PANELS_DIR"
cd /home/bernt-popp/development/kidney-genetics-db

for file in $PANELS_DIR/*.json; do
    provider=$(basename "$file" .json)
    echo "Uploading $provider..."

    response=$(curl -s -X POST "http://localhost:8000/api/ingestion/DiagnosticPanels/upload" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$file" \
        -F "mode=full")

    # Check response
    if echo "$response" | jq -e '.data' > /dev/null 2>&1; then
        echo "  ✓ Success: $(echo "$response" | jq -r '.data.message // "Uploaded"')"
    else
        echo "  ✗ Error: $(echo "$response" | jq -r '.error.detail // "Unknown error"')"
    fi
done

echo "Upload complete!"