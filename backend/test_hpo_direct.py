#!/usr/bin/env python3
"""Direct test of HPO API to verify it works."""

import asyncio
import httpx
import json

async def test_hpo_api():
    """Test HPO API directly."""
    
    async with httpx.AsyncClient() as client:
        # Test descendants endpoint
        url = "https://ontology.jax.org/api/hp/terms/HP:0010935/descendants"
        print(f"Testing: {url}")
        
        response = await client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} descendants")
            
            # Test annotation for one term
            if data:
                test_term = data[0] if isinstance(data[0], str) else data[0].get('id', data[0])
                ann_url = f"https://ontology.jax.org/api/network/annotation/{test_term}"
                print(f"\nTesting annotation: {ann_url}")
                
                ann_response = await client.get(ann_url)
                print(f"Status: {ann_response.status_code}")
                
                if ann_response.status_code == 200:
                    ann_data = ann_response.json()
                    genes = ann_data.get("genes", [])
                    print(f"Found {len(genes)} genes")
                    if genes:
                        print(f"First gene: {genes[0].get('name', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(test_hpo_api())