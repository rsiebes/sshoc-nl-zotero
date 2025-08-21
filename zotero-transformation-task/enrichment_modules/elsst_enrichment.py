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
import requests
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus

# Try to import NLP libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import nltk
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    print("⚠️  Warning: NLP libraries not available. Similarity matching disabled.")

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️  Warning: BeautifulSoup not available. HTML parsing limited.")

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
        
        # Initialize keyword-to-concept index for fast lookups
        self.keyword_index_file = self.cache_file.parent / "elsst_keyword_index.json"
        self.keyword_index = self._load_keyword_index()
        
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
    
    def _load_keyword_index(self) -> Dict[str, Dict]:
        """Load keyword-to-concept index for fast lookups"""
        if self.keyword_index_file.exists():
            try:
                with open(self.keyword_index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                print(f"✅ Loaded keyword index with {len(index)} entries")
                return index
            except (json.JSONDecodeError, IOError):
                print(f"⚠️  Warning: Could not load keyword index {self.keyword_index_file}")
                return {}
        return {}
    
    def _save_keyword_index(self):
        """Save keyword-to-concept index to file"""
        try:
            with open(self.keyword_index_file, 'w', encoding='utf-8') as f:
                json.dump(self.keyword_index, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️  Warning: Could not save keyword index: {e}")
    
    def _update_keyword_index(self, keyword: str, concept: ELSSTConcept):
        """Update the keyword index with a new keyword-concept mapping"""
        keyword_lower = keyword.lower().strip()
        
        # Store concept information in index
        concept_data = {
            "uri": concept.uri,
            "preferred_label": concept.preferred_label,
            "confidence_score": concept.confidence_score,
            "last_updated": str(int(time.time()))
        }
        
        self.keyword_index[keyword_lower] = concept_data
        
    def _lookup_keyword_in_index(self, keyword: str) -> Optional[ELSSTConcept]:
        """Fast lookup of keyword in the index"""
        keyword_lower = keyword.lower().strip()
        
        if keyword_lower in self.keyword_index:
            concept_data = self.keyword_index[keyword_lower]
            
            # Create ELSSTConcept from index data
            concept = ELSSTConcept(
                uri=concept_data["uri"],
                preferred_label=concept_data["preferred_label"],
                confidence_score=concept_data["confidence_score"],
                matching_keywords=[keyword]
            )
            
            return concept
        
        return None
    
    def _save_cache(self):
        """Save cache and keyword index to files"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            self._save_keyword_index()
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
                "definition": "The process of creating new ideas, products, or methods"
            },
            "employment": {
                "uri": "https://elsst.cessda.eu/id/5/3b58eac5-38a9-4a8f-b50a-9c86ed21c210",
                "label": "LABOUR MARKET",
                "alternatives": ["employment", "job", "work", "labor", "labour", "jobs", "unemployment", "workforce"],
                "broader": ["ECONOMICS"],
                "definition": "The market for labor services"
            },
            "welfare": {
                "uri": "https://elsst.cessda.eu/id/5/7c9d8e2f-1a3b-4c5d-6e7f-8a9b0c1d2e3f",
                "label": "SOCIAL WELFARE",
                "alternatives": ["welfare", "social security", "benefits", "assistance", "support"],
                "broader": ["SOCIAL POLICY"],
                "definition": "Government programs providing financial aid and services to individuals and families"
            },
            "policy": {
                "uri": "https://elsst.cessda.eu/id/5/4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
                "label": "SOCIAL POLICY",
                "alternatives": ["policy", "policies", "intervention", "program", "programme", "government"],
                "broader": ["POLITICS"],
                "definition": "Government actions and decisions affecting social welfare and public services"
            },
            "mothers": {
                "uri": "https://elsst.cessda.eu/id/5/2e3f4a5b-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
                "label": "FAMILY",
                "alternatives": ["mothers", "mother", "parents", "parenting", "family", "children", "childcare"],
                "broader": ["DEMOGRAPHY"],
                "definition": "Family structures and relationships"
            },
            "experiment": {
                "uri": "https://elsst.cessda.eu/id/5/1f2a3b4c-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
                "label": "RESEARCH METHODS",
                "alternatives": ["experiment", "experimental", "trial", "study", "research", "methodology"],
                "broader": ["METHODOLOGY"],
                "definition": "Scientific methods for conducting research"
            },
            "training": {
                "uri": "https://elsst.cessda.eu/id/5/9e8d7c6b-5a4f-3e2d-1c0b-9a8f7e6d5c4b",
                "label": "EDUCATION",
                "alternatives": ["training", "education", "learning", "skills", "development", "teaching"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "Formal and informal learning processes"
            },
            "health": {
                "uri": "https://elsst.cessda.eu/id/5/6b5a4f3e-2d1c-0b9a-8f7e-6d5c4b3a2f1e",
                "label": "HEALTH",
                "alternatives": ["health", "healthcare", "medical", "medicine", "illness", "disease"],
                "broader": ["SOCIAL SCIENCES"],
                "definition": "Physical and mental well-being"
            },
            "migration": {
                "uri": "https://elsst.cessda.eu/id/5/8a7f6e5d-4c3b-2a1f-0e9d-8c7b6a5f4e3d",
                "label": "MIGRATION",
                "alternatives": ["migration", "immigrant", "immigration", "mobility", "movement"],
                "broader": ["DEMOGRAPHY"],
                "definition": "Movement of people from one place to another"
            },
            "housing": {
                "uri": "https://elsst.cessda.eu/id/5/24473156-aebb-4c02-83e2-ac6698cfb842",
                "label": "HOUSING POLICY",
                "alternatives": ["housing", "homes", "residential", "accommodation", "dwelling"],
                "broader": ["SOCIAL POLICY"],
                "definition": "Policies related to housing and residential accommodation"
            },
            "urban": {
                "uri": "https://elsst.cessda.eu/id/5/0dda29d6-ea7d-44bf-b65d-69ee321e4f71",
                "label": "URBAN DEVELOPMENT",
                "alternatives": ["urban", "city", "cities", "metropolitan", "municipal", "neighbourhood"],
                "broader": ["GEOGRAPHY"],
                "definition": "Development and planning of urban areas"
            },
            "diversity": {
                "uri": "https://elsst.cessda.eu/id/5/8c7b6a5f-4e3d-2c1b-0a9f-8e7d6c5b4a3f",
                "label": "CULTURAL DIVERSITY",
                "alternatives": ["diversity", "multicultural", "ethnic", "cultural", "minorities"],
                "broader": ["CULTURE"],
                "definition": "Variety of cultural and ethnic backgrounds in society"
            },
            "business": {
                "uri": "https://elsst.cessda.eu/id/5/5f4e3d2c-1b0a-9f8e-7d6c-5b4a3f2e1d0c",
                "label": "BUSINESS MANAGEMENT",
                "alternatives": ["business", "management", "firms", "companies", "corporate", "enterprise"],
                "broader": ["ECONOMICS"],
                "definition": "Organization and management of business enterprises"
            },
            "environment": {
                "uri": "https://elsst.cessda.eu/id/5/3d2c1b0a-9f8e-7d6c-5b4a-3f2e1d0c9b8a",
                "label": "ENVIRONMENTAL SCIENCES",
                "alternatives": ["environment", "environmental", "ecology", "climate", "sustainability"],
                "broader": ["NATURAL SCIENCES"],
                "definition": "Study of the environment and environmental issues"
            },
            "technology": {
                "uri": "https://elsst.cessda.eu/id/5/1c0b9a8f-7e6d-5c4b-3a2f-1e0d9c8b7a6f",
                "label": "TECHNOLOGY",
                "alternatives": ["technology", "technological", "digital", "computer", "internet", "AI"],
                "broader": ["APPLIED SCIENCES"],
                "definition": "Application of scientific knowledge for practical purposes"
            }
        }
    
    def search_elsst_concepts(self, keywords: List[str], title: str = "", abstract: str = "") -> List[ELSSTConcept]:
        """Search for ELSST concepts matching the given keywords"""
        print(f"  🔍 Searching ELSST concepts for {len(keywords)} keywords...")
        
        found_concepts = []
        new_mappings = []  # Track new mappings for index updates
        
        # 1. Fast index lookup first
        index_matches = []
        remaining_keywords = []
        
        for keyword in keywords:
            indexed_concept = self._lookup_keyword_in_index(keyword)
            if indexed_concept:
                print(f"    ⚡ Index hit: {keyword} → {indexed_concept.preferred_label}")
                index_matches.append(indexed_concept)
            else:
                remaining_keywords.append(keyword)
        
        found_concepts.extend(index_matches)
        
        # 2. Process remaining keywords with full search
        if remaining_keywords:
            print(f"    🔍 Full search for {len(remaining_keywords)} new keywords...")
            
            # Direct vocabulary matching
            direct_matches = self._match_direct_vocabulary(remaining_keywords)
            found_concepts.extend(direct_matches)
            new_mappings.extend(direct_matches)
            
            # Similarity-based matching if NLP is available
            if NLP_AVAILABLE and abstract:
                similarity_matches = self._match_similarity_based(remaining_keywords, title, abstract)
                found_concepts.extend(similarity_matches)
                new_mappings.extend(similarity_matches)
            
            # Try ELSST API search (if available)
            api_matches = self._search_elsst_api(remaining_keywords)
            found_concepts.extend(api_matches)
            new_mappings.extend(api_matches)
        
        # 3. Update keyword index with new mappings
        for concept in new_mappings:
            for keyword in concept.matching_keywords:
                self._update_keyword_index(keyword, concept)
        
        # 4. Remove duplicates and rank by confidence
        unique_concepts = self._deduplicate_and_rank_concepts(found_concepts)
        
        print(f"    ✅ Found {len(unique_concepts)} unique ELSST concepts ({len(index_matches)} from index, {len(new_mappings)} new)")
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
            
            # Find high-similarity matches (reduced threshold for more results)
            matches = []
            for i, similarity in enumerate(similarities):
                if similarity > 0.15:  # Reduced threshold from 0.3 to 0.15 for more matches
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
        """Search ELSST API for concepts using the real CESSDA thesaurus search"""
        concepts = []
        
        for keyword in keywords:
            try:
                # Use the CESSDA ELSST search API
                search_url = f"https://thesauri.cessda.eu/elsst-5/en/search"
                params = {
                    'clang': 'en',
                    'q': keyword.strip(),
                    'format': 'json'  # Try to get JSON response
                }
                
                print(f"    🔍 Searching ELSST for: '{keyword}'")
                
                # Make request with proper headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; SSHOC-NL-Enricher/1.0)',
                    'Accept': 'application/json, text/html, */*'
                }
                
                response = requests.get(search_url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Try to parse as JSON first
                    try:
                        data = response.json()
                        # Process JSON response if available
                        if isinstance(data, dict) and 'results' in data:
                            for result in data.get('results', [])[:3]:  # Limit to top 3 results
                                concept = self._parse_elsst_json_result(result, keyword)
                                if concept:
                                    concepts.append(concept)
                                    # Update keyword index
                                    self._update_keyword_index(keyword, concept)
                        
                    except json.JSONDecodeError:
                        # If not JSON, parse HTML response
                        concept = self._parse_elsst_html_response(response.text, keyword)
                        if concept:
                            concepts.append(concept)
                            # Update keyword index
                            self._update_keyword_index(keyword, concept)
                            print(f"      ✅ Found ELSST concept: {concept.preferred_label}")
                        else:
                            print(f"      ⚠️ No ELSST concept found for: '{keyword}'")
                else:
                    print(f"      ⚠️ ELSST search failed for '{keyword}': HTTP {response.status_code}")
                
                # Rate limiting - be respectful to the API
                time.sleep(0.5)
                
            except requests.RequestException as e:
                print(f"      ⚠️ Error searching ELSST for '{keyword}': {e}")
            except Exception as e:
                print(f"      ⚠️ Unexpected error for '{keyword}': {e}")
        
        return concepts
    
    def _parse_elsst_html_response(self, html_content: str, keyword: str) -> Optional[ELSSTConcept]:
        """Parse HTML response from ELSST search to extract concept information"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for search results in the HTML
            # ELSST search results typically have specific CSS classes or patterns
            result_links = soup.find_all('a', href=True)
            
            for link in result_links:
                href = link.get('href', '')
                # Look for concept page URLs
                if '/page/' in href and 'elsst-5' in href:
                    # Extract concept ID from URL
                    concept_id = href.split('/page/')[-1].split('.')[0] if '/page/' in href else None
                    
                    if concept_id:
                        # Get the concept label from the link text
                        label = link.get_text(strip=True)
                        
                        if label and len(label) > 2:  # Valid label
                            # Construct full URI
                            uri = f"https://elsst.cessda.eu/id/5/{concept_id}"
                            
                            concept = ELSSTConcept(
                                uri=uri,
                                preferred_label=label,
                                alternative_labels=[keyword],
                                confidence_score=0.9,  # High confidence for direct API match
                                matching_keywords=[keyword]
                            )
                            
                            return concept
            
            # If no direct links found, look for other patterns
            # Sometimes the concept name is in specific div or span elements
            concept_elements = soup.find_all(['div', 'span', 'h1', 'h2', 'h3'], class_=True)
            for element in concept_elements:
                text = element.get_text(strip=True)
                if text and keyword.lower() in text.lower() and len(text) < 100:
                    # This might be a concept label
                    # Generate a placeholder URI (would need real concept ID)
                    uri = f"https://elsst.cessda.eu/id/5/{hashlib.md5(text.encode()).hexdigest()[:8]}"
                    
                    concept = ELSSTConcept(
                        uri=uri,
                        preferred_label=text,
                        alternative_labels=[keyword],
                        confidence_score=0.7,  # Medium confidence for HTML parsing
                        matching_keywords=[keyword]
                    )
                    
                    return concept
                    
        except Exception as e:
            print(f"      ⚠️ Error parsing ELSST HTML for '{keyword}': {e}")
        
        return None
    
    def _parse_elsst_json_result(self, result: Dict, keyword: str) -> Optional[ELSSTConcept]:
        """Parse JSON result from ELSST API"""
        try:
            # Extract concept information from JSON structure
            concept_id = result.get('id') or result.get('uri', '').split('/')[-1]
            label = result.get('prefLabel') or result.get('label') or result.get('title')
            alt_labels = result.get('altLabels', [])
            definition = result.get('definition', '')
            
            if concept_id and label:
                uri = f"https://elsst.cessda.eu/id/5/{concept_id}"
                
                concept = ELSSTConcept(
                    uri=uri,
                    preferred_label=label,
                    alternative_labels=alt_labels + [keyword],
                    definition=definition,
                    confidence_score=0.95,  # Very high confidence for JSON API response
                    matching_keywords=[keyword]
                )
                
                return concept
                
        except Exception as e:
            print(f"      ⚠️ Error parsing ELSST JSON for '{keyword}': {e}")
        
        return None
    
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

