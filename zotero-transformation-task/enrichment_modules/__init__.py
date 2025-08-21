"""
Enrichment Modules Package for SSHOC-NL Zotero Pipeline

This package contains specialized modules for enriching metadata from various sources:
- author_enrichment: ORCID integration and author profile enrichment
- Future modules: ELSST vocabulary, geographic data, keywords, etc.

Each module follows a consistent pattern:
1. Data source integration (APIs, databases, etc.)
2. Intelligent caching for performance
3. Structured output compatible with RDF/Turtle
4. Error handling and graceful fallbacks
5. Standalone CLI and Python API interfaces

Usage:
    from enrichment_modules.author_enrichment import AuthorEnricher, AuthorInfo
    
Author: SSHOC-NL Development Team
Date: August 2025
Version: 2.1.0
"""

# Import main classes for easy access
from .author_enrichment import AuthorEnricher, AuthorInfo
from .keyword_abstract_enrichment import KeywordAbstractEnricher, ContentInfo

__version__ = "2.1.0"
__author__ = "SSHOC-NL Development Team"

# Package metadata
__all__ = [
    "AuthorEnricher",
    "AuthorInfo",
    "KeywordAbstractEnricher", 
    "ContentInfo",
]

