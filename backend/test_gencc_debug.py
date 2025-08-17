#!/usr/bin/env python3
"""Debug GenCC to see why it's not finding kidney genes."""

import asyncio
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.pipeline.sources.gencc_cached import GenCCClientCached
from app.core.cache_service import get_cache_service

async def test_gencc():
    # Setup database
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Initialize GenCC client
        cache_service = get_cache_service(db)
        client = GenCCClientCached(cache_service=cache_service, db_session=db)
        
        print("📥 Downloading GenCC file...")
        file_path = await client.download_excel_file()
        
        if file_path:
            print(f"✅ File downloaded: {file_path}")
            
            print("\n📊 Parsing Excel file...")
            df = await client.parse_excel_file(file_path)
            
            if not df.empty:
                print(f"✅ Parsed {len(df)} total submissions")
                print(f"\n📋 Column names in file:")
                for col in df.columns:
                    print(f"  - {col}")
                
                # Sample the first few rows
                print(f"\n🔍 First 3 rows of data:")
                for idx, row in df.head(3).iterrows():
                    print(f"\n--- Row {idx} ---")
                    for col in ['gene_symbol', 'disease_title', 'classification']:
                        if col in df.columns:
                            print(f"  {col}: {row[col]}")
                
                # Check for kidney-related submissions
                print(f"\n🔎 Checking for kidney-related submissions...")
                kidney_count = 0
                kidney_samples = []
                
                for idx, row in df.iterrows():
                    if client.is_kidney_related(row):
                        kidney_count += 1
                        if len(kidney_samples) < 5:
                            gene_info = client.extract_gene_info(row)
                            if gene_info:
                                kidney_samples.append(gene_info)
                
                print(f"✅ Found {kidney_count} kidney-related submissions")
                
                if kidney_samples:
                    print(f"\n📌 Sample kidney-related genes:")
                    for sample in kidney_samples:
                        print(f"  - {sample['symbol']}: {sample['disease_name'][:50]}...")
                else:
                    # Manually search for kidney keywords
                    print(f"\n🔍 Manually searching for kidney keywords...")
                    kidney_keywords = ["kidney", "renal", "nephro", "glomerul", 
                                     "tubul", "polycystic", "alport", "nephritis"]
                    
                    for keyword in kidney_keywords:
                        matching_rows = df[df.apply(lambda row: any(
                            keyword in str(val).lower() if pd.notna(val) else False 
                            for val in row
                        ), axis=1)]
                        
                        if not matching_rows.empty:
                            print(f"\n  Found {len(matching_rows)} rows with keyword '{keyword}'")
                            sample_row = matching_rows.iloc[0]
                            print(f"    Sample: {sample_row.get('gene_symbol', 'N/A')} - {sample_row.get('disease_title', 'N/A')[:50]}")
            else:
                print("❌ DataFrame is empty!")
        else:
            print("❌ Failed to download file!")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_gencc())