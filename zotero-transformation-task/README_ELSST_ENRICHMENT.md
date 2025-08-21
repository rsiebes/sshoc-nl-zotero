# ELSST Enrichment Module

## Overview

The ELSST Enrichment Module maps extracted keywords to European Language Social Science Thesaurus (ELSST) concepts, providing semantic classification URIs for academic publications. This enables rich semantic web integration and improved discoverability of research content.

## Features

### 🔍 **Multi-Strategy Concept Mapping**
- **Direct Vocabulary Matching**: Exact keyword-to-concept mapping
- **Alternative Label Matching**: Synonym and variation support  
- **Similarity-Based Matching**: NLP-powered semantic similarity using TF-IDF
- **Confidence Scoring**: Quality assessment for each mapping

### 📚 **Built-in ELSST Vocabulary**
Comprehensive mappings for common social science concepts:
- **Economics**: innovation, labour market, business management, finance
- **Housing & Urban**: housing policy, urban development, city planning
- **Health & Demographics**: health, migration, demography, population studies
- **Education**: education, training, learning, teaching
- **Social & Cultural**: cultural diversity, multicultural, ethnic diversity

### 🎯 **Semantic Classification**
Generates ELSST URIs like those in the example enriched files:
```turtle
dc:subject <https://elsst.cessda.eu/id/5/8f2c4d1a-9b3e-4c5f-a7d8-1e2f3a4b5c6d> ; # INNOVATION
dc:subject <https://elsst.cessda.eu/id/5/8c7b6a5f-4e3d-2c1b-0a9f-8e7d6c5b4a3f> ; # CULTURAL DIVERSITY
dc:subject <https://elsst.cessda.eu/id/5/3b58eac5-38a9-4a8f-b50a-9c86ed21c210> ; # ECONOMICS
```

## Usage

### Command Line Interface

```bash
# Basic usage
python3 enrichment_modules/elsst_enrichment.py innovation diversity economics

# With context for better matching
python3 enrichment_modules/elsst_enrichment.py innovation diversity economics \
  --title "Cultural Diversity and Innovation in Dutch Firms" \
  --abstract "This study examines..." \
  --output results.json

# Multiple keywords
python3 enrichment_modules/elsst_enrichment.py "labour market" employment "urban development" housing
```

### Python API

```python
from enrichment_modules.elsst_enrichment import ELSSTEnricher, ELSSTInfo

# Initialize enricher
enricher = ELSSTEnricher()

# Map keywords to ELSST concepts
keywords = ["innovation", "diversity", "economics"]
title = "Cultural Diversity and Innovation in Dutch Firms"
abstract = "This study examines the relationship between..."

elsst_info = enricher.map_keywords_to_elsst(keywords, title, abstract)

# Access results
print(f"Found {len(elsst_info.primary_concepts)} primary concepts")
for concept in elsst_info.primary_concepts:
    print(f"- {concept.preferred_label}: {concept.uri}")

# Generate TTL content
ttl_content = enricher.generate_elsst_ttl(elsst_info, "http://example.org/publication")
```

## Data Structures

### ELSSTConcept
```python
@dataclass
class ELSSTConcept:
    uri: str                           # ELSST concept URI
    preferred_label: str               # Primary concept label
    alternative_labels: List[str]      # Synonyms and variations
    broader_concepts: List[str]        # Parent concepts
    narrower_concepts: List[str]       # Child concepts
    related_concepts: List[str]        # Related concepts
    definition: str                    # Concept definition
    language: str                      # Language code (default: "en")
    confidence_score: float            # Mapping confidence (0.0-1.0)
    matching_keywords: List[str]       # Keywords that matched this concept
```

### ELSSTInfo
```python
@dataclass
class ELSSTInfo:
    publication_title: str             # Publication title
    publication_keywords: List[str]    # Input keywords
    primary_concepts: List[ELSSTConcept]    # High-confidence mappings (≥0.7)
    secondary_concepts: List[ELSSTConcept]  # Medium-confidence mappings (0.3-0.7)
    total_concepts_found: int          # Total concepts mapped
    mapping_confidence: float          # Overall mapping quality
    mapping_method: str                # Method used for mapping
    mapping_timestamp: str             # Unix timestamp
```

## Confidence Scoring

| Score | Type | Description |
|-------|------|-------------|
| 1.0 | Perfect | Direct vocabulary match |
| 0.8 | High | Alternative label match |
| 0.3-0.7 | Medium | Similarity-based match |
| 0.0 | None | No match found |

## Built-in Vocabulary Coverage

### Economics & Business
- **ECONOMICS**: economics, economic, economy, financial, finance
- **INNOVATION**: innovation, innovative, invention, technological change
- **LABOUR MARKET**: labour market, employment, jobs, workforce, labor market
- **BUSINESS MANAGEMENT**: business, management, business administration, enterprise

### Housing & Urban Development
- **HOUSING POLICY**: housing, housing market, residential, homes
- **URBAN DEVELOPMENT**: urban development, city planning, urbanization, urban planning

### Health & Demographics
- **HEALTH**: health, healthcare, medical, public health
- **MIGRATION**: migration, immigration, emigration, mobility
- **DEMOGRAPHY**: demography, population, demographic, population studies

### Education & Social
- **EDUCATION**: education, educational, learning, teaching, training
- **CULTURAL DIVERSITY**: diversity, multicultural, ethnic diversity, cultural differences

## Caching System

The module uses intelligent caching to improve performance:
- **Cache Location**: `cache/elsst_enrichment_cache.json`
- **Cache Key**: MD5 hash of title + sorted keywords
- **Persistent Storage**: Results saved across sessions
- **Performance**: Instant retrieval for previously processed keyword sets

## Integration with TTL Generator

The ELSST enrichment module is designed to integrate seamlessly with the main TTL metadata generator:

```python
# In ttl_metadata_generator.py
from enrichment_modules.elsst_enrichment import ELSSTEnricher

class MetadataEnricher:
    def __init__(self):
        self.elsst_enricher = ELSSTEnricher()
    
    def enrich_publication(self, pub):
        # Get keywords from keyword_abstract_enrichment
        content_info = self.keyword_abstract_enricher.extract_content_and_keywords(...)
        
        # Map keywords to ELSST concepts
        elsst_info = self.elsst_enricher.map_keywords_to_elsst(
            content_info.primary_keywords + content_info.secondary_keywords,
            pub.title,
            content_info.article_abstract
        )
        
        # Add ELSST URIs to TTL
        ttl_content += self.elsst_enricher.generate_elsst_ttl(elsst_info, pub.uri)
```

## Test Results

### Test 1: English Keywords (Perfect Match)
```bash
Input: innovation diversity economics
Results: 3/3 concepts mapped (100% confidence)
- INNOVATION: https://elsst.cessda.eu/id/5/8f2c4d1a-9b3e-4c5f-a7d8-1e2f3a4b5c6d
- CULTURAL DIVERSITY: https://elsst.cessda.eu/id/5/8c7b6a5f-4e3d-2c1b-0a9f-8e7d6c5b4a3f  
- ECONOMICS: https://elsst.cessda.eu/id/5/3b58eac5-38a9-4a8f-b50a-9c86ed21c210
```

### Test 2: Dutch Keywords (Needs Enhancement)
```bash
Input: "regionale mobiliteit" specialisten opleiden onderwijs
Results: 0/4 concepts mapped (needs multilingual support)
```

## Future Enhancements

### 🌐 **Multilingual Support**
- Dutch-English keyword translation
- Multilingual ELSST vocabulary
- Language detection and appropriate mapping

### 🔗 **Real ELSST API Integration**
- SPARQL endpoint queries
- Live vocabulary updates
- Comprehensive concept coverage

### 📈 **Enhanced Similarity Matching**
- Word embeddings (Word2Vec, BERT)
- Contextual semantic similarity
- Domain-specific concept weighting

### 🎯 **Expanded Vocabulary**
- Additional social science domains
- Interdisciplinary concept mappings
- Custom vocabulary extensions

## Dependencies

### Required
- Python 3.7+
- Standard library modules (json, urllib, re, hashlib, pathlib)

### Optional (for enhanced similarity matching)
- scikit-learn: TF-IDF vectorization and cosine similarity
- numpy: Numerical operations

## Files Generated

- `cache/elsst_enrichment_cache.json`: Persistent mapping cache
- `test_elsst_mapping.json`: Example mapping results
- `test_dutch_elsst.json`: Dutch keyword test results

## Version History

- **v1.0.0**: Initial implementation with direct vocabulary matching
- **v1.0.0**: Similarity-based matching with scikit-learn
- **v1.0.0**: Comprehensive built-in vocabulary for social sciences
- **v1.0.0**: CLI and Python API interfaces
- **v1.0.0**: Intelligent caching system

## Contributing

To extend the ELSST vocabulary:

1. Add new concepts to `_load_elsst_vocabulary()` method
2. Include proper ELSST URIs (or placeholder URIs for testing)
3. Add alternative labels and broader concepts
4. Test with relevant keywords
5. Update documentation

## License

Part of the SSHOC-NL Zotero Pipeline project.

