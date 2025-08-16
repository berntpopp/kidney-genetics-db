#!/usr/bin/env python3
"""
Debug script to check HGNC ID normalization issues
"""

from app.core.database import get_db
from sqlalchemy import text

def main():
    # Get database session
    db = next(get_db())

    print("=== HGNC ID Normalization Diagnostic ===\n")

    # Check genes without HGNC IDs  
    result = db.execute(text("SELECT approved_symbol, hgnc_id FROM genes WHERE hgnc_id IS NULL OR hgnc_id = '' LIMIT 10")).fetchall()
    print('Genes without HGNC IDs (first 10):')
    for row in result:
        print(f'  {row[0]} - HGNC: {row[1]}')

    print()

    # Check specific gene ABCA4
    result = db.execute(text("SELECT approved_symbol, hgnc_id FROM genes WHERE approved_symbol = 'ABCA4'")).fetchone()
    if result:
        print(f'ABCA4 - HGNC: {result[1]}')
    else:
        print('ABCA4 not found')

    print()

    # Check total genes with/without HGNC IDs
    result = db.execute(text('SELECT COUNT(*) as total FROM genes')).fetchone()
    total_genes = result[0]

    result = db.execute(text("SELECT COUNT(*) as with_hgnc FROM genes WHERE hgnc_id IS NOT NULL AND hgnc_id != ''")).fetchone()
    with_hgnc = result[0]

    print(f'Total genes: {total_genes}')
    print(f'With HGNC ID: {with_hgnc}')
    print(f'Without HGNC ID: {total_genes - with_hgnc}')
    print(f'Percentage without HGNC ID: {((total_genes - with_hgnc) / total_genes * 100):.1f}%')

    print()

    # Check which sources are creating genes without HGNC IDs
    result = db.execute(text("""
    SELECT DISTINCT ge.source_name, COUNT(DISTINCT g.id) as count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id 
    WHERE g.hgnc_id IS NULL OR g.hgnc_id = ''
    GROUP BY ge.source_name
    ORDER BY count DESC
    """)).fetchall()

    print('Sources creating genes without HGNC IDs:')
    for row in result:
        print(f'  {row[0]}: {row[1]} genes')

    print()

    # Show examples of genes from each problematic source
    for source_name, _ in result[:3]:  # Top 3 sources
        print(f"Examples from {source_name}:")
        examples = db.execute(text("""
        SELECT DISTINCT g.approved_symbol, g.hgnc_id
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id 
        WHERE (g.hgnc_id IS NULL OR g.hgnc_id = '') 
        AND ge.source_name = :source_name
        LIMIT 5
        """), {"source_name": source_name}).fetchall()
        
        for example in examples:
            print(f'  {example[0]} - HGNC: {example[1]}')
        print()

    db.close()

if __name__ == "__main__":
    main()