#!/bin/bash
for i in {1..20}; do
  echo "=== Check $i at $(date) ==="
  curl -s "http://localhost:8000/api/progress/status" | jq '.[] | select(.source_name == "HPO") | {status, current_operation, current_item, total_items}'
  
  # Also check if any HPO evidence created
  uv run python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM gene_evidence WHERE source_name = \\'HPO\\''))
    count = result.scalar()
    print(f'HPO evidence count: {count}')
" 2>/dev/null
  
  sleep 30
done