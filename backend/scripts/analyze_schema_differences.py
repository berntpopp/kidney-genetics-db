#!/usr/bin/env python
"""Analyze ALL schema differences between SQLAlchemy models and PostgreSQL database."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from app.core.config import settings
from app.models import *  # Import all models
from app.models.base import Base
import json

def get_db_schema(engine):
    """Get complete database schema."""
    inspector = inspect(engine)
    schema = {}

    for table_name in inspector.get_table_names():
        table_info = {
            'columns': {},
            'indexes': {},
            'foreign_keys': [],
            'unique_constraints': [],
            'check_constraints': []
        }

        # Get columns
        for col in inspector.get_columns(table_name):
            col_info = {
                'type': str(col['type']),
                'nullable': col['nullable'],
                'default': str(col['default']) if col['default'] else None,
                'autoincrement': col.get('autoincrement', False)
            }
            table_info['columns'][col['name']] = col_info

        # Get indexes
        for idx in inspector.get_indexes(table_name):
            table_info['indexes'][idx['name']] = {
                'columns': idx['column_names'],
                'unique': idx['unique']
            }

        # Get foreign keys
        for fk in inspector.get_foreign_keys(table_name):
            table_info['foreign_keys'].append({
                'name': fk['name'],
                'constrained_columns': fk['constrained_columns'],
                'referred_table': fk['referred_table'],
                'referred_columns': fk['referred_columns']
            })

        # Get unique constraints
        for uc in inspector.get_unique_constraints(table_name):
            if uc['name']:
                table_info['unique_constraints'].append({
                    'name': uc['name'],
                    'columns': uc['column_names']
                })

        # Get check constraints
        for cc in inspector.get_check_constraints(table_name):
            table_info['check_constraints'].append({
                'name': cc['name'],
                'sqltext': str(cc['sqltext'])
            })

        schema[table_name] = table_info

    return schema

def get_model_schema(base):
    """Get schema from SQLAlchemy models."""
    schema = {}

    for mapper in base.registry.mappers:
        table = mapper.mapped_table
        if table is None:
            continue

        table_name = table.name
        table_info = {
            'columns': {},
            'indexes': {},
            'foreign_keys': [],
            'unique_constraints': [],
            'check_constraints': []
        }

        # Get columns
        for col in table.columns:
            col_info = {
                'type': str(col.type.compile(dialect=postgresql.dialect())),
                'nullable': col.nullable,
                'default': str(col.server_default) if col.server_default else None,
                'autoincrement': col.autoincrement if hasattr(col, 'autoincrement') else False
            }
            table_info['columns'][col.name] = col_info

        # Get indexes
        for idx in table.indexes:
            table_info['indexes'][idx.name] = {
                'columns': [c.name for c in idx.columns],
                'unique': idx.unique
            }

        # Get foreign keys
        for fk in table.foreign_keys:
            fk_info = {
                'name': fk.constraint.name if fk.constraint else None,
                'constrained_columns': [fk.parent.name],
                'referred_table': fk.column.table.name,
                'referred_columns': [fk.column.name]
            }
            # Avoid duplicates
            if fk_info not in table_info['foreign_keys']:
                table_info['foreign_keys'].append(fk_info)

        # Get constraints
        for constraint in table.constraints:
            if constraint.name and hasattr(constraint, 'columns'):
                if hasattr(constraint, 'unique') and constraint.unique:
                    table_info['unique_constraints'].append({
                        'name': constraint.name,
                        'columns': [c.name for c in constraint.columns]
                    })

        schema[table_name] = table_info

    return schema

def compare_schemas(db_schema, model_schema):
    """Compare database schema with model schema and return ALL differences."""
    differences = {
        'tables_only_in_db': [],
        'tables_only_in_models': [],
        'column_differences': {},
        'index_differences': {},
        'foreign_key_differences': {},
        'constraint_differences': {}
    }

    all_tables = set(db_schema.keys()) | set(model_schema.keys())

    # Find table differences
    differences['tables_only_in_db'] = sorted(set(db_schema.keys()) - set(model_schema.keys()))
    differences['tables_only_in_models'] = sorted(set(model_schema.keys()) - set(db_schema.keys()))

    # Compare common tables
    common_tables = set(db_schema.keys()) & set(model_schema.keys())

    for table in sorted(common_tables):
        db_table = db_schema[table]
        model_table = model_schema[table]

        # Column differences
        col_diffs = []

        # Columns only in DB
        db_only_cols = set(db_table['columns'].keys()) - set(model_table['columns'].keys())
        for col in sorted(db_only_cols):
            col_diffs.append({
                'issue': 'column_only_in_db',
                'column': col,
                'db_type': db_table['columns'][col]['type']
            })

        # Columns only in models
        model_only_cols = set(model_table['columns'].keys()) - set(db_table['columns'].keys())
        for col in sorted(model_only_cols):
            col_diffs.append({
                'issue': 'column_only_in_model',
                'column': col,
                'model_type': model_table['columns'][col]['type']
            })

        # Compare common columns
        common_cols = set(db_table['columns'].keys()) & set(model_table['columns'].keys())
        for col in sorted(common_cols):
            db_col = db_table['columns'][col]
            model_col = model_table['columns'][col]

            # Type differences
            db_type = db_col['type'].upper().replace(' ', '')
            model_type = model_col['type'].upper().replace(' ', '')

            # Normalize types for comparison
            type_mappings = {
                'TIMESTAMP': 'TIMESTAMP',
                'TIMESTAMPWITHOUTTIMEZONE': 'TIMESTAMP',
                'TIMESTAMPWITHTIMEZONE': 'TIMESTAMPWITHTIMEZONE',
                'VARCHAR': 'VARCHAR',
                'CHARACTERVARYING': 'VARCHAR',
                'TEXT': 'TEXT',
                'INTEGER': 'INTEGER',
                'BIGINT': 'BIGINT',
                'BOOLEAN': 'BOOLEAN',
                'JSONB': 'JSONB',
                'JSON': 'JSON',
                'UUID': 'UUID',
                'DOUBLE PRECISION': 'FLOAT',
                'DOUBLEPRECISION': 'FLOAT',
                'FLOAT': 'FLOAT'
            }

            # Extract base type without size
            import re
            db_base = re.sub(r'\([^)]*\)', '', db_type)
            model_base = re.sub(r'\([^)]*\)', '', model_type)

            for old, new in type_mappings.items():
                db_base = db_base.replace(old, new)
                model_base = model_base.replace(old, new)

            if db_base != model_base:
                # Special case: TIMESTAMP vs TIMESTAMP WITH TIME ZONE
                if 'TIMESTAMP' in db_base and 'TIMESTAMP' in model_base:
                    if 'TIMEZONE' in db_base and 'TIMEZONE' not in model_base:
                        col_diffs.append({
                            'issue': 'timezone_mismatch',
                            'column': col,
                            'db_has_timezone': True,
                            'model_has_timezone': False
                        })
                    elif 'TIMEZONE' not in db_base and 'TIMEZONE' in model_base:
                        col_diffs.append({
                            'issue': 'timezone_mismatch',
                            'column': col,
                            'db_has_timezone': False,
                            'model_has_timezone': True
                        })
                else:
                    col_diffs.append({
                        'issue': 'type_mismatch',
                        'column': col,
                        'db_type': db_col['type'],
                        'model_type': model_col['type']
                    })

            # Nullable differences
            if db_col['nullable'] != model_col['nullable']:
                col_diffs.append({
                    'issue': 'nullable_mismatch',
                    'column': col,
                    'db_nullable': db_col['nullable'],
                    'model_nullable': model_col['nullable']
                })

            # Default differences
            db_default = db_col['default']
            model_default = model_col['default']
            if db_default != model_default:
                # Ignore some common equivalent defaults
                if not (
                    (db_default is None and model_default in ['NULL', 'null']) or
                    (model_default is None and db_default in ['NULL', 'null'])
                ):
                    col_diffs.append({
                        'issue': 'default_mismatch',
                        'column': col,
                        'db_default': db_default,
                        'model_default': model_default
                    })

        if col_diffs:
            differences['column_differences'][table] = col_diffs

        # Index differences
        idx_diffs = []

        # Indexes only in DB
        db_only_idx = set(db_table['indexes'].keys()) - set(model_table['indexes'].keys())
        for idx in sorted(db_only_idx):
            idx_diffs.append({
                'issue': 'index_only_in_db',
                'index': idx,
                'columns': db_table['indexes'][idx]['columns']
            })

        # Indexes only in models
        model_only_idx = set(model_table['indexes'].keys()) - set(db_table['indexes'].keys())
        for idx in sorted(model_only_idx):
            idx_diffs.append({
                'issue': 'index_only_in_model',
                'index': idx,
                'columns': model_table['indexes'][idx]['columns']
            })

        if idx_diffs:
            differences['index_differences'][table] = idx_diffs

    return differences

def main():
    """Main function to analyze differences."""
    print("=" * 80)
    print("COMPLETE SCHEMA DIFFERENCE ANALYSIS")
    print("=" * 80)

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # Get schemas
    print("\nGathering database schema...")
    db_schema = get_db_schema(engine)

    print("Gathering model schema...")
    model_schema = get_model_schema(Base)

    # Compare
    print("\nComparing schemas...")
    differences = compare_schemas(db_schema, model_schema)

    # Count total differences
    total_diffs = 0

    # Report differences
    if differences['tables_only_in_db']:
        print(f"\n### Tables Only in Database ({len(differences['tables_only_in_db'])})")
        for table in differences['tables_only_in_db']:
            print(f"  - {table}")
            total_diffs += 1

    if differences['tables_only_in_models']:
        print(f"\n### Tables Only in Models ({len(differences['tables_only_in_models'])})")
        for table in differences['tables_only_in_models']:
            print(f"  - {table}")
            total_diffs += 1

    if differences['column_differences']:
        print(f"\n### Column Differences ({sum(len(v) for v in differences['column_differences'].values())} total)")
        for table, diffs in sorted(differences['column_differences'].items()):
            print(f"\n  Table: {table}")
            for diff in diffs:
                if diff['issue'] == 'column_only_in_db':
                    print(f"    - DB ONLY: {diff['column']} ({diff['db_type']})")
                    total_diffs += 1
                elif diff['issue'] == 'column_only_in_model':
                    print(f"    - MODEL ONLY: {diff['column']} ({diff['model_type']})")
                    total_diffs += 1
                elif diff['issue'] == 'type_mismatch':
                    print(f"    - TYPE: {diff['column']}: DB={diff['db_type']} vs Model={diff['model_type']}")
                    total_diffs += 1
                elif diff['issue'] == 'timezone_mismatch':
                    print(f"    - TIMEZONE: {diff['column']}: DB={'WITH TZ' if diff['db_has_timezone'] else 'NO TZ'} vs Model={'WITH TZ' if diff['model_has_timezone'] else 'NO TZ'}")
                    total_diffs += 1
                elif diff['issue'] == 'nullable_mismatch':
                    print(f"    - NULLABLE: {diff['column']}: DB={diff['db_nullable']} vs Model={diff['model_nullable']}")
                    total_diffs += 1
                elif diff['issue'] == 'default_mismatch':
                    print(f"    - DEFAULT: {diff['column']}: DB={diff['db_default']} vs Model={diff['model_default']}")
                    total_diffs += 1

    if differences['index_differences']:
        print(f"\n### Index Differences ({sum(len(v) for v in differences['index_differences'].values())} total)")
        for table, diffs in sorted(differences['index_differences'].items()):
            print(f"\n  Table: {table}")
            for diff in diffs:
                if diff['issue'] == 'index_only_in_db':
                    print(f"    - DB ONLY: {diff['index']} on {diff['columns']}")
                    total_diffs += 1
                elif diff['issue'] == 'index_only_in_model':
                    print(f"    - MODEL ONLY: {diff['index']} on {diff['columns']}")
                    total_diffs += 1

    print("\n" + "=" * 80)
    print(f"TOTAL DIFFERENCES FOUND: {total_diffs}")
    print("=" * 80)

    # Save detailed JSON report
    with open('schema_differences.json', 'w') as f:
        json.dump(differences, f, indent=2, default=str)
    print("\nDetailed report saved to: schema_differences.json")

    return total_diffs

if __name__ == "__main__":
    total = main()
    sys.exit(0 if total == 0 else 1)