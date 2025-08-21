#!/usr/bin/env python3
"""
Build Keyword Index from Existing ELSST Cache

This script processes the existing ELSST enrichment cache and builds
a keyword-to-concept index for faster lookups. This prevents the need
to rebuild mappings that have already been discovered.

Usage:
    python3 build_keyword_index.py
"""

import json
from pathlib import Path
from typing import Dict, List

def build_keyword_index_from_cache():
    """Build keyword index from existing ELSST cache"""
    
    cache_dir = Path("cache")
    cache_file = cache_dir / "elsst_enrichment_cache.json"
    index_file = cache_dir / "elsst_keyword_index.json"
    
    print("🔧 Building ELSST Keyword Index from Cache")
    print("=" * 50)
    
    # Load existing cache
    if not cache_file.exists():
        print(f"❌ Cache file not found: {cache_file}")
        return
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    except Exception as e:
        print(f"❌ Error loading cache: {e}")
        return
    
    print(f"✅ Loaded cache with {len(cache)} entries")
    
    # Build keyword index
    keyword_index = {}
    total_keywords = 0
    
    for cache_key, cache_data in cache.items():
        publication_title = cache_data.get("publication_title", "")
        
        # Process primary concepts
        for concept in cache_data.get("primary_concepts", []):
            for keyword in concept.get("matching_keywords", []):
                keyword_lower = keyword.lower().strip()
                
                # Store concept information in index
                concept_data = {
                    "uri": concept["uri"],
                    "preferred_label": concept["preferred_label"],
                    "confidence_score": concept["confidence_score"],
                    "last_updated": cache_data.get("mapping_timestamp", "0"),
                    "source": "cache_rebuild"
                }
                
                keyword_index[keyword_lower] = concept_data
                total_keywords += 1
                
                print(f"  📝 {keyword} → {concept['preferred_label']}")
        
        # Process secondary concepts
        for concept in cache_data.get("secondary_concepts", []):
            for keyword in concept.get("matching_keywords", []):
                keyword_lower = keyword.lower().strip()
                
                # Only add if not already present (primary concepts have priority)
                if keyword_lower not in keyword_index:
                    concept_data = {
                        "uri": concept["uri"],
                        "preferred_label": concept["preferred_label"],
                        "confidence_score": concept["confidence_score"],
                        "last_updated": cache_data.get("mapping_timestamp", "0"),
                        "source": "cache_rebuild"
                    }
                    
                    keyword_index[keyword_lower] = concept_data
                    total_keywords += 1
                    
                    print(f"  📝 {keyword} → {concept['preferred_label']} (secondary)")
    
    # Save keyword index
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(keyword_index, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Built keyword index with {len(keyword_index)} unique keywords")
        print(f"💾 Saved to: {index_file}")
        
        # Display statistics
        print(f"\n📊 Index Statistics:")
        print(f"  - Unique keywords: {len(keyword_index)}")
        print(f"  - Total mappings processed: {total_keywords}")
        print(f"  - Cache entries processed: {len(cache)}")
        
        # Show sample entries
        print(f"\n🔍 Sample Index Entries:")
        for i, (keyword, concept_data) in enumerate(list(keyword_index.items())[:5]):
            print(f"  {i+1}. '{keyword}' → {concept_data['preferred_label']} (confidence: {concept_data['confidence_score']})")
        
        if len(keyword_index) > 5:
            print(f"  ... and {len(keyword_index) - 5} more entries")
            
    except Exception as e:
        print(f"❌ Error saving keyword index: {e}")
        return
    
    print(f"\n🎉 Keyword index built successfully!")

if __name__ == "__main__":
    build_keyword_index_from_cache()

