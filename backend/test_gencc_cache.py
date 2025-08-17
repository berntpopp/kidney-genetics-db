#!/usr/bin/env python3
"""Test GenCC caching to see what's failing."""

import asyncio
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.pipeline.sources.gencc_cached import GenCCClientCached
from app.core.cache_service import get_cache_service

async def test_gencc_cache():
    # Setup database
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Initialize GenCC client
        cache_service = get_cache_service(db)
        client = GenCCClientCached(cache_service=cache_service, db_session=db)
        
        print("📥 Testing GenCC kidney gene data fetch...")
        
        # Call the function directly without caching to see what it returns
        async def fetch_and_process_data():
            # Download Excel file
            file_path = await client.download_excel_file()
            if not file_path:
                print("❌ Failed to download GenCC file")
                return {}
            
            # Parse Excel file  
            df = await client.parse_excel_file(file_path)
            if df.empty:
                print("❌ Failed to parse GenCC file or file is empty")
                return {}
            
            print(f"📊 Parsed {len(df)} total submissions")
            
            # Process submissions for kidney-related genes
            gene_data_map = {}
            kidney_related_count = 0
            
            for idx, row in df.iterrows():
                # Filter for kidney-related submissions
                if not client.is_kidney_related(row):
                    continue
                
                kidney_related_count += 1
                
                # Extract gene information
                gene_info = client.extract_gene_info(row)
                if not gene_info:
                    continue
                
                symbol = gene_info["symbol"]
                
                # Aggregate by gene symbol
                if symbol not in gene_data_map:
                    gene_data_map[symbol] = {
                        "symbol": symbol,
                        "hgnc_id": gene_info["hgnc_id"],
                        "submissions": [],
                        "disease_count": 0,
                        "submitter_count": 0,
                        "classifications": {},
                        "submitters": set(),
                        "diseases": set(),
                    }
                
                # Add submission
                gene_data_map[symbol]["submissions"].append(gene_info)
                gene_data_map[symbol]["submitters"].add(gene_info["submitter"])
                gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
                
                # Count classifications
                classification = gene_info["classification"]
                if classification:
                    if classification not in gene_data_map[symbol]["classifications"]:
                        gene_data_map[symbol]["classifications"][classification] = 0
                    gene_data_map[symbol]["classifications"][classification] += 1
            
            # Finalize aggregated data
            for symbol, data in gene_data_map.items():
                data["disease_count"] = len(data["diseases"])
                data["submitter_count"] = len(data["submitters"])
                data["submission_count"] = len(data["submissions"])
                
                # Convert sets to lists for JSON serialization
                data["submitters"] = list(data["submitters"])
                data["diseases"] = list(data["diseases"])
            
            print(f"✅ Processed {kidney_related_count} kidney-related submissions")
            print(f"📊 Found {len(gene_data_map)} unique kidney-related genes")
            
            if gene_data_map:
                sample_genes = list(gene_data_map.keys())[:3]
                print(f"📌 Sample genes found: {sample_genes}")
            
            return gene_data_map
        
        # Run the fetch function directly
        result = await fetch_and_process_data()
        
        if result:
            print(f"\n✅ Got {len(result)} genes from direct fetch")
            
            # Try to serialize it to JSON to see if there are issues
            try:
                json_str = json.dumps(result)
                print(f"✅ Result is JSON serializable ({len(json_str)} chars)")
            except Exception as e:
                print(f"❌ Result is NOT JSON serializable: {e}")
                
                # Find the problematic data
                for gene, data in result.items():
                    try:
                        json.dumps(data)
                    except Exception as e2:
                        print(f"  Problem in gene {gene}: {e2}")
                        # Check each field
                        for field, value in data.items():
                            try:
                                json.dumps(value)
                            except Exception as e3:
                                print(f"    Field '{field}' is not serializable: {type(value)}")
                                if field == "submissions" and isinstance(value, list):
                                    # Check each submission
                                    for i, sub in enumerate(value):
                                        try:
                                            json.dumps(sub)
                                        except Exception as e4:
                                            print(f"      Submission {i} has problem: {e4}")
                                            for k, v in sub.items():
                                                try:
                                                    json.dumps(v)
                                                except:
                                                    print(f"        Field '{k}' = {v} ({type(v)})")
                        break
            
            # Now try to cache it
            print("\n📦 Testing cache storage...")
            try:
                success = await cache_service.set("test_kidney_gene_data", result, "gencc", 3600)
                if success:
                    print("✅ Successfully cached the result")
                else:
                    print("❌ Failed to cache the result")
            except Exception as e:
                print(f"❌ Cache error: {e}")
        else:
            print("❌ No data returned from fetch")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_gencc_cache())