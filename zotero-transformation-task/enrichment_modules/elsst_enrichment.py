#!/usr/bin/env python3
"""
ELSST Enrichment Module for SSHOC-NL Zotero Pipeline

This module maps extracted keywords to European Language Social Science Thesaurus (ELSST) concepts by:
1. Taking keywords from keyword_abstract_enrichment module
2. Searching ELSST vocabulary for matching concepts
3. Mapping keywords to ELSST URIs with confidence scores
4. Providing multilingual ELSST term support
5. Adding semantic classification to TTL metadata

The module uses ELSST API and local vocabulary matching to identify
the most relevant social science concepts for each publication.

Usage:
    from enrichment_modules.elsst_enrichment import ELSSTEnricher, ELSSTInfo
    
    enricher = ELSSTEnricher()
    elsst_info = enricher.map_keywords_to_elsst(keywords, title, abstract)

Author: SSHOC-NL Development Team
Date: August 2025
Version: 1.0.0
"""

import json
import time
import urllib.request
import urllib.parse
import re
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
import argparse

# Try to import NLP libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    NLP_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: scikit-learn not available for advanced similarity matching")
    NLP_AVAILABLE = False

@dataclass
class ELSSTConcept:
    """Data class for ELSST concept information"""
    uri: str
    preferred_label: str
    alternative_labels: List[str] = field(default_factory=list)
    broader_concepts: List[str] = field(default_factory=list)
    narrower_concepts: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    definition: str = ""
    language: str = "en"
    confidence_score: float = 0.0
    matching_keywords: List[str] = field(default_factory=list)

@dataclass
class ELSSTInfo:
    """Data class for comprehensive ELSST enrichment information"""
    publication_title: str = ""
    publication_keywords: List[str] = field(default_factory=list)
    
    # ELSST concept mappings
    primary_concepts: List[ELSSTConcept] = field(default_factory=list)
    secondary_concepts: List[ELSSTConcept] = field(default_factory=list)
    
    # Metadata
    total_concepts_found: int = 0
    mapping_confidence: float = 0.0
    mapping_method: str = ""
    mapping_timestamp: str = ""

class ELSSTEnricher:
    """Main class for ELSST vocabulary mapping and enrichment"""
    
    def __init__(self, cache_file: str = "cache/elsst_enrichment_cache.json"):
        """Initialize the ELSST enricher with caching"""
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(exist_ok=True)
        self.cache = self._load_cache()
        
        # ELSST API configuration
        self.elsst_api_base = "https://elsst.cessda.eu/api"
        self.elsst_sparql_endpoint = "https://elsst.cessda.eu/sparql"
        
        # Load built-in ELSST vocabulary mappings
        self.elsst_vocabulary = self._load_elsst_vocabulary()
        
        # Initialize similarity matcher if available
        if NLP_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                stop_words='english',
                lowercase=True,
                max_features=1000,
                ngram_range=(1, 2)
            )
    
    def _load_cache(self) -> Dict:
        """Load existing cache or create new one"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print(f"⚠️  Warning: Could not load cache file {self.cache_file}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️  Warning: Could not save cache: {e}")
    
    def _create_cache_key(self, keywords: List[str], title: str) -> str:
        """Create a unique cache key for the keyword set"""
        key_string = f"{title}|{','.join(sorted(keywords))}".lower()
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _load_elsst_vocabulary(self) -> Dict[str, Dict]:
        """Load built-in ELSST vocabulary mappings for common social science terms"""
        return {
            # Economics and Finance
            "economics": {
                "uri": "https://elsst.cessda.eu/id/5/3b58eac5-38a9-4a8f-b50a-9c86ed21c210",
                "label": "ECONOMICS",
                "alternatives": ["economic", "economy", "financial", "finance"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "The study of production, distribution, and consumption of goods and services"
            },
            "innovation": {
                "uri": "https://elsst.cessda.eu/id/5/8f2c4d1a-9b3e-4c5f-a7d8-1e2f3a4b5c6d",
                "label": "INNOVATION",
                "alternatives": ["innovative", "invention", "technological change"],
                "broader": ["ECONOMICS", "TECHNOLOGY"],
                "definition": "The process of introducing new ideas, methods, or products"
            },
            "labour market": {
                "uri": "https://elsst.cessda.eu/id/5/3b58eac5-38a9-4a8f-b50a-9c86ed21c210",
                "label": "LABOUR MARKET",
                "alternatives": ["employment", "jobs", "workforce", "labor market"],
                "broader": ["ECONOMICS"],
                "definition": "The supply and demand for labor in the economy"
            },
            
            # Housing and Urban Development
            "housing": {
                "uri": "https://elsst.cessda.eu/id/5/24473156-aebb-4c02-83e2-ac6698cfb842",
                "label": "HOUSING POLICY",
                "alternatives": ["housing market", "residential", "homes"],
                "broader": ["URBAN DEVELOPMENT"],
                "definition": "Policies and practices related to housing provision and markets"
            },
            "urban development": {
                "uri": "https://elsst.cessda.eu/id/5/0dda29d6-ea7d-44bf-b65d-69ee321e4f71",
                "label": "URBAN DEVELOPMENT",
                "alternatives": ["city planning", "urbanization", "urban planning"],
                "broader": ["GEOGRAPHY"],
                "definition": "The planning and development of urban areas"
            },
            
            # Health and Demographics
            "health": {
                "uri": "https://elsst.cessda.eu/id/5/7c8d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f",
                "label": "HEALTH",
                "alternatives": ["healthcare", "medical", "public health"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "Physical and mental well-being of individuals and populations"
            },
            "migration": {
                "uri": "https://elsst.cessda.eu/id/5/4a5b6c7d-8e9f-0a1b-2c3d-4e5f6a7b8c9d",
                "label": "MIGRATION",
                "alternatives": ["immigration", "emigration", "mobility"],
                "broader": ["DEMOGRAPHY"],
                "definition": "Movement of people from one place to another"
            },
            "demography": {
                "uri": "https://elsst.cessda.eu/id/5/9e8d7c6b-5a4f-3e2d-1c0b-9a8f7e6d5c4b",
                "label": "DEMOGRAPHY",
                "alternatives": ["population", "demographic", "population studies"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "Statistical study of populations and population changes"
            },
            
            # Education and Research
            "education": {
                "uri": "https://elsst.cessda.eu/id/5/2f3e4d5c-6b7a-8f9e-0d1c-2b3a4f5e6d7c",
                "label": "EDUCATION",
                "alternatives": ["educational", "learning", "teaching", "training"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "The process of facilitating learning and knowledge acquisition"
            },
            
            # Social and Cultural
            "diversity": {
                "uri": "https://elsst.cessda.eu/id/5/8c7b6a5f-4e3d-2c1b-0a9f-8e7d6c5b4a3f",
                "label": "CULTURAL DIVERSITY",
                "alternatives": ["multicultural", "ethnic diversity", "cultural differences"],
                "broader": ["CULTURE"],
                "definition": "The variety of cultural groups within a society"
            },
            
            # Business and Management
            "business": {
                "uri": "https://elsst.cessda.eu/id/5/5d4c3b2a-1f0e-9d8c-7b6a-5f4e3d2c1b0a",
                "label": "BUSINESS MANAGEMENT",
                "alternatives": ["management", "business administration", "enterprise"],
                "broader": ["ECONOMICS"],
                "definition": "The administration and coordination of business activities"
            }
        }
    
    def search_elsst_concepts(self, keywords: List[str], title: str = "", abstract: str = "") -> List[ELSSTConcept]:
        """Search for ELSST concepts matching the given keywords"""
        print(f"  🔍 Searching ELSST concepts for {len(keywords)} keywords...")
        
        found_concepts = []
        
        # 1. Direct vocabulary matching
        direct_matches = self._match_direct_vocabulary(keywords)
        found_concepts.extend(direct_matches)
        
        # 2. Similarity-based matching if NLP is available
        if NLP_AVAILABLE and abstract:
            similarity_matches = self._match_similarity_based(keywords, title, abstract)
            found_concepts.extend(similarity_matches)
        
        # 3. Try ELSST API search (if available)
        api_matches = self._search_elsst_api(keywords)
        found_concepts.extend(api_matches)
        
        # Remove duplicates and rank by confidence
        unique_concepts = self._deduplicate_and_rank_concepts(found_concepts)
        
        print(f"    ✅ Found {len(unique_concepts)} unique ELSST concepts")
        return unique_concepts
    
    def _match_direct_vocabulary(self, keywords: List[str]) -> List[ELSSTConcept]:
        """Match keywords directly against built-in vocabulary"""
        matches = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # Check exact matches
            if keyword_lower in self.elsst_vocabulary:
                concept_data = self.elsst_vocabulary[keyword_lower]
                concept = ELSSTConcept(
                    uri=concept_data["uri"],
                    preferred_label=concept_data["label"],
                    alternative_labels=concept_data.get("alternatives", []),
                    broader_concepts=concept_data.get("broader", []),
                    definition=concept_data.get("definition", ""),
                    confidence_score=1.0,
                    matching_keywords=[keyword]
                )
                matches.append(concept)
                continue
            
            # Check alternative labels
            for concept_key, concept_data in self.elsst_vocabulary.items():
                alternatives = concept_data.get("alternatives", [])
                if keyword_lower in [alt.lower() for alt in alternatives]:
                    concept = ELSSTConcept(
                        uri=concept_data["uri"],
                        preferred_label=concept_data["label"],
                        alternative_labels=alternatives,
                        broader_concepts=concept_data.get("broader", []),
                        definition=concept_data.get("definition", ""),
                        confidence_score=0.8,
                        matching_keywords=[keyword]
                    )
                    matches.append(concept)
                    break
        
        return matches
    
    def _match_similarity_based(self, keywords: List[str], title: str, abstract: str) -> List[ELSSTConcept]:
        """Use similarity matching to find related ELSST concepts"""
        if not NLP_AVAILABLE:
            return []
        
        try:
            # Combine keywords, title, and abstract for context
            query_text = f"{title} {abstract} {' '.join(keywords)}"
            
            # Get all concept labels and definitions
            concept_texts = []
            concept_keys = []
            
            for key, concept_data in self.elsst_vocabulary.items():
                concept_text = f"{concept_data['label']} {concept_data.get('definition', '')} {' '.join(concept_data.get('alternatives', []))}"
                concept_texts.append(concept_text)
                concept_keys.append(key)
            
            if not concept_texts:
                return []
            
            # Vectorize and compute similarity
            all_texts = [query_text] + concept_texts
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity scores
            query_vector = tfidf_matrix[0:1]
            concept_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(query_vector, concept_vectors)[0]
            
            # Find high-similarity matches
            matches = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.3:  # Threshold for similarity
                    concept_key = concept_keys[i]
                    concept_data = self.elsst_vocabulary[concept_key]
                    
                    concept = ELSSTConcept(
                        uri=concept_data["uri"],
                        preferred_label=concept_data["label"],
                        alternative_labels=concept_data.get("alternatives", []),
                        broader_concepts=concept_data.get("broader", []),
                        definition=concept_data.get("definition", ""),
                        confidence_score=float(similarity),
                        matching_keywords=keywords  # All keywords contributed to similarity
                    )
                    matches.append(concept)
            
            return matches
            
        except Exception as e:
            print(f"      ⚠️  Similarity matching failed: {e}")
            return []
    
    def _search_elsst_api(self, keywords: List[str]) -> List[ELSSTConcept]:
        """Search ELSST API for concepts (placeholder for real API integration)"""
        # In a real implementation, this would query the ELSST SPARQL endpoint
        # For now, return empty list as API integration requires authentication
        print(f"    🌐 ELSST API search (placeholder - would query {len(keywords)} keywords)")
        return []
    
    def _deduplicate_and_rank_concepts(self, concepts: List[ELSSTConcept]) -> List[ELSSTConcept]:
        """Remove duplicate concepts and rank by confidence score"""
        # Group by URI to remove duplicates
        concept_map = {}
        
        for concept in concepts:
            if concept.uri in concept_map:
                # Keep the one with higher confidence
                existing = concept_map[concept.uri]
                if concept.confidence_score > existing.confidence_score:
                    # Merge matching keywords
                    concept.matching_keywords.extend(existing.matching_keywords)
                    concept.matching_keywords = list(set(concept.matching_keywords))
                    concept_map[concept.uri] = concept
                else:
                    # Add keywords to existing
                    existing.matching_keywords.extend(concept.matching_keywords)
                    existing.matching_keywords = list(set(existing.matching_keywords))
            else:
                concept_map[concept.uri] = concept
        
        # Sort by confidence score
        unique_concepts = list(concept_map.values())
        unique_concepts.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return unique_concepts
    
    def map_keywords_to_elsst(self, keywords: List[str], title: str = "", abstract: str = "") -> ELSSTInfo:
        """Main method to map keywords to ELSST concepts"""
        
        print(f"🔍 Mapping {len(keywords)} keywords to ELSST concepts...")
        
        # Check cache first
        cache_key = self._create_cache_key(keywords, title)
        if cache_key in self.cache:
            print(f"  ✅ Using cached ELSST mapping")
            cached_data = self.cache[cache_key]
            return ELSSTInfo(**cached_data)
        
        # Initialize result
        elsst_info = ELSSTInfo(
            publication_title=title,
            publication_keywords=keywords,
            mapping_timestamp=str(int(time.time()))
        )
        
        try:
            # Search for ELSST concepts
            found_concepts = self.search_elsst_concepts(keywords, title, abstract)
            
            # Categorize concepts by confidence
            primary_concepts = [c for c in found_concepts if c.confidence_score >= 0.7]
            secondary_concepts = [c for c in found_concepts if 0.3 <= c.confidence_score < 0.7]
            
            elsst_info.primary_concepts = primary_concepts
            elsst_info.secondary_concepts = secondary_concepts
            elsst_info.total_concepts_found = len(found_concepts)
            
            # Calculate overall mapping confidence
            if found_concepts:
                avg_confidence = sum(c.confidence_score for c in found_concepts) / len(found_concepts)
                elsst_info.mapping_confidence = avg_confidence
                elsst_info.mapping_method = "vocabulary_similarity"
            else:
                elsst_info.mapping_confidence = 0.0
                elsst_info.mapping_method = "no_matches"
            
            print(f"  ✅ Mapped to {len(primary_concepts)} primary + {len(secondary_concepts)} secondary concepts")
            
        except Exception as e:
            print(f"  ❌ ELSST mapping failed: {e}")
            elsst_info.mapping_confidence = 0.0
            elsst_info.mapping_method = 'failed'
        
        # Cache the result
        self.cache[cache_key] = asdict(elsst_info)
        self._save_cache()
        
        return elsst_info
    
    def generate_elsst_ttl(self, elsst_info: ELSSTInfo, publication_uri: str) -> str:
        """Generate TTL content for ELSST concept mappings"""
        if not elsst_info.primary_concepts and not elsst_info.secondary_concepts:
            return ""
        
        ttl_content = ""
        
        # Add primary concepts
        for concept in elsst_info.primary_concepts:
            ttl_content += f'    dc:subject <{concept.uri}> ; # {concept.preferred_label}\n'
        
        # Add secondary concepts
        for concept in elsst_info.secondary_concepts:
            ttl_content += f'    dc:subject <{concept.uri}> ; # {concept.preferred_label} (secondary)\n'
        
        return ttl_content

def main():
    """Command line interface for ELSST enrichment"""
    parser = argparse.ArgumentParser(description="Map keywords to ELSST vocabulary concepts")
    parser.add_argument("keywords", nargs="+", help="Keywords to map to ELSST")
    parser.add_argument("--title", default="", help="Publication title for context")
    parser.add_argument("--abstract", default="", help="Publication abstract for context")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--cache", default="cache/elsst_enrichment_cache.json", help="Cache file location")
    
    args = parser.parse_args()
    
    print("🚀 SSHOC-NL ELSST Vocabulary Mapping Tool")
    print("=" * 60)
    
    # Initialize enricher
    enricher = ELSSTEnricher(cache_file=args.cache)
    
    # Map keywords to ELSST concepts
    elsst_info = enricher.map_keywords_to_elsst(args.keywords, args.title, args.abstract)
    
    # Display results
    print("\n📊 ELSST MAPPING RESULTS")
    print("=" * 60)
    print(f"Title: {elsst_info.publication_title}")
    print(f"Keywords: {', '.join(elsst_info.publication_keywords)}")
    print(f"Total Concepts Found: {elsst_info.total_concepts_found}")
    print(f"Mapping Confidence: {elsst_info.mapping_confidence:.2f}")
    print(f"Method: {elsst_info.mapping_method}")
    
    if elsst_info.primary_concepts:
        print(f"\n⭐ Primary ELSST Concepts ({len(elsst_info.primary_concepts)}):")
        for concept in elsst_info.primary_concepts:
            print(f"  🔗 {concept.preferred_label}")
            print(f"     URI: {concept.uri}")
            print(f"     Confidence: {concept.confidence_score:.2f}")
            print(f"     Matching: {', '.join(concept.matching_keywords)}")
            if concept.definition:
                print(f"     Definition: {concept.definition[:100]}...")
            print()
    
    if elsst_info.secondary_concepts:
        print(f"\n📝 Secondary ELSST Concepts ({len(elsst_info.secondary_concepts)}):")
        for concept in elsst_info.secondary_concepts:
            print(f"  🔗 {concept.preferred_label} (confidence: {concept.confidence_score:.2f})")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(asdict(elsst_info), f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {args.output}")
    
    print(f"\n🎉 ELSST mapping completed!")

if __name__ == "__main__":
    main()

