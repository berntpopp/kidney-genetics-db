#!/usr/bin/env python
"""Clean all data from database while keeping structure."""

from sqlalchemy import create_engine, text
from app.core.config import settings

def clean_database():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        tables = ['gene_annotations', 'gene_evidence', 'gene_curations', 'data_source_progress', 'genes']
        for table in tables:
            try:
                result = conn.execute(text(f'TRUNCATE TABLE {table} CASCADE'))
                conn.commit()
                print(f'  ✓ Truncated {table}')
            except Exception as e:
                print(f'  Warning: {table}: {e}')

if __name__ == "__main__":
    clean_database()