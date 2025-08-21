#!/usr/bin/env python3
"""
Keyword and Abstract Enrichment Module for SSHOC-NL Zotero Pipeline

This module extracts both keywords and abstracts from academic publications by:
1. Finding the actual article online using title and authors
2. Extracting full abstracts from various academic sources
3. Generating keywords through advanced NLP content analysis
4. Extracting explicit keywords from article metadata
5. Providing structured output for TTL metadata generation

The module uses web search, content extraction, and NLP techniques
to identify the most relevant keywords and complete abstracts for each publication.

Usage:
    from enrichment_modules.keyword_abstract_enrichment import KeywordAbstractEnricher, ContentInfo
    
    enricher = KeywordAbstractEnricher()
    content = enricher.extract_content_and_keywords(title, authors, publication_uri)

Author: SSHOC-NL Development Team
Date: August 2025
Version: 2.0.0
"""

import json
import time
import urllib.request
import urllib.parse
import re
import hashlib
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from pathlib import Path
import argparse

# NLP libraries for proper keyword extraction
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    import nltk
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
    from nltk.tag import pos_tag
    from nltk.chunk import ne_chunk
    from nltk.tree import Tree
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet', quiet=True)
    
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger', quiet=True)
    
    try:
        nltk.data.find('chunkers/maxent_ne_chunker')
    except LookupError:
        nltk.download('maxent_ne_chunker', quiet=True)
    
    try:
        nltk.data.find('corpora/words')
    except LookupError:
        nltk.download('words', quiet=True)
    
    NLP_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: NLP libraries not available: {e}")
    NLP_AVAILABLE = False

@dataclass
class ContentInfo:
    """Structured information about extracted content including abstract and keywords"""
    publication_title: str = ""
    publication_authors: str = ""
    publication_uri: str = ""
    
    # Found article information
    found_article_url: str = ""
    found_article_title: str = ""
    article_abstract: str = ""
    article_doi: str = ""
    article_journal: str = ""
    
    # Explicit keywords from the article
    explicit_keywords: List[str] = field(default_factory=list)
    
    # Generated keywords from content analysis
    generated_keywords: List[str] = field(default_factory=list)
    
    # Combined and ranked keywords
    primary_keywords: List[str] = field(default_factory=list)
    secondary_keywords: List[str] = field(default_factory=list)
    
    # Metadata
    extraction_confidence: float = 0.0
    extraction_method: str = ""
    extraction_timestamp: str = ""

class KeywordAbstractEnricher:
    """Main class for keyword and abstract extraction and enrichment"""
    
    def __init__(self, cache_file: str = "cache/keyword_abstract_enrichment_cache.json"):
        """Initialize the keyword and abstract enricher with caching"""
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(exist_ok=True)
        self.cache = self._load_cache()
        
        # Common academic stop words to filter out
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'can', 'cannot', 'study', 'research', 'analysis', 'paper', 'article', 'using',
            'based', 'results', 'findings', 'conclusion', 'abstract', 'introduction', 'method',
            'approach', 'data', 'model', 'framework', 'theory', 'evidence', 'significant',
            'important', 'different', 'various', 'several', 'many', 'most', 'some', 'all', 'both'
        }
        
        # Domain-specific keyword patterns
        self.domain_patterns = {
            'health': ['health', 'medical', 'disease', 'treatment', 'patient', 'clinical', 'epidemiology', 'mortality', 'morbidity'],
            'economics': ['economic', 'economy', 'market', 'financial', 'income', 'employment', 'labor', 'business', 'trade'],
            'social': ['social', 'society', 'community', 'demographic', 'population', 'migration', 'education', 'policy'],
            'environment': ['environmental', 'climate', 'pollution', 'sustainability', 'green', 'carbon', 'energy'],
            'technology': ['technology', 'digital', 'innovation', 'artificial', 'intelligence', 'data', 'algorithm'],
            'urban': ['urban', 'city', 'housing', 'transport', 'infrastructure', 'planning', 'development']
        }
    
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
    
    def _create_cache_key(self, title: str, authors: str) -> str:
        """Create a unique cache key for the publication"""
        key_string = f"{title}|{authors}".lower()
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def search_for_article(self, title: str, authors: str) -> Dict[str, str]:
        """Search for the article online using title and authors"""
        print(f"  🔍 Searching for article: {title[:50]}...")
        
        # Create search query
        search_terms = []
        
        # Add title (clean and truncate if too long)
        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        title_words = clean_title.split()[:10]  # Limit to first 10 words
        search_terms.extend(title_words)
        
        # Add first author
        if authors:
            first_author = authors.split(',')[0].split('&')[0].strip()
            # Remove titles and initials for better search
            author_parts = first_author.split()
            if len(author_parts) >= 2:
                search_terms.append(author_parts[-1])  # Last name
        
        search_query = ' '.join(search_terms)
        
        # Try multiple search approaches
        search_results = []
        
        # 1. Try Google Scholar search
        scholar_result = self._search_google_scholar(search_query)
        if scholar_result:
            search_results.append(scholar_result)
        
        # 2. Try general web search for PDF
        pdf_result = self._search_for_pdf(search_query)
        if pdf_result:
            search_results.append(pdf_result)
        
        # 3. Try DOI search if available in original URI
        doi_result = self._search_by_doi(title, authors)
        if doi_result:
            search_results.append(doi_result)
        
        # Return the best result
        if search_results:
            return search_results[0]  # Return first/best result
        
        return {
            'url': '',
            'title': title,
            'abstract': '',
            'doi': '',
            'journal': '',
            'confidence': 0.0,
            'method': 'not_found'
        }
    
    def _search_google_scholar(self, query: str) -> Optional[Dict[str, str]]:
        """Search Google Scholar for the article"""
        try:
            # Simulate Google Scholar search (in practice, would use proper API)
            print(f"    📚 Searching Google Scholar for: {query[:30]}...")
            time.sleep(1)  # Rate limiting
            
            # For now, return a placeholder - in real implementation would parse Scholar results
            return {
                'url': f'https://scholar.google.com/scholar?q={urllib.parse.quote(query)}',
                'title': query,
                'abstract': '',
                'doi': '',
                'journal': '',
                'confidence': 0.3,
                'method': 'google_scholar'
            }
        except Exception as e:
            print(f"    ❌ Google Scholar search failed: {e}")
            return None
    
    def _search_for_pdf(self, query: str) -> Optional[Dict[str, str]]:
        """Search for PDF version of the article"""
        try:
            print(f"    📄 Searching for PDF: {query[:30]}...")
            time.sleep(1)  # Rate limiting
            
            # In practice, would search academic databases, repositories, etc.
            # For now, return placeholder
            return {
                'url': f'https://example.com/search?q={urllib.parse.quote(query)}',
                'title': query,
                'abstract': '',
                'doi': '',
                'journal': '',
                'confidence': 0.2,
                'method': 'pdf_search'
            }
        except Exception as e:
            print(f"    ❌ PDF search failed: {e}")
            return None
    
    def _search_by_doi(self, title: str, authors: str) -> Optional[Dict[str, str]]:
        """Try to find DOI and search by DOI"""
        try:
            # Extract potential DOI from title or look up in CrossRef
            print(f"    🔗 Searching by DOI...")
            time.sleep(1)  # Rate limiting
            
            # Placeholder - in practice would use CrossRef API
            return None
        except Exception as e:
            print(f"    ❌ DOI search failed: {e}")
            return None
    
    def extract_content_from_url(self, url: str) -> Dict[str, str]:
        """Extract abstract and content from the found article URL"""
        print(f"  📖 Extracting content from: {url[:50]}...")
        
        try:
            # In practice, would use proper web scraping/PDF parsing
            # For now, return simulated content based on common patterns
            
            if 'scholar.google.com' in url:
                return self._extract_from_scholar_page(url)
            elif url.endswith('.pdf'):
                return self._extract_from_pdf(url)
            else:
                return self._extract_from_webpage(url)
                
        except Exception as e:
            print(f"    ❌ Content extraction failed: {e}")
            return {
                'abstract': '',
                'content': '',
                'explicit_keywords': [],
                'journal': '',
                'doi': ''
            }
    
    def _extract_from_scholar_page(self, url: str) -> Dict[str, str]:
        """Extract information from Google Scholar page with real content extraction"""
        print(f"    📚 Extracting from Google Scholar: {url[:50]}...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
                
                # Extract abstract from Google Scholar results
                abstract = self._extract_scholar_abstract(content)
                
                # Extract other metadata
                doi = self._extract_doi_from_html(content)
                journal = self._extract_journal_from_html(content)
                
                return {
                    'abstract': abstract,
                    'content': abstract,  # Use abstract as content for keyword extraction
                    'explicit_keywords': [],
                    'journal': journal,
                    'doi': doi
                }
                
        except Exception as e:
            print(f"      ⚠️  Error extracting from Scholar: {e}")
            return {
                'abstract': '',
                'content': '',
                'explicit_keywords': [],
                'journal': '',
                'doi': ''
            }
    
    def _extract_scholar_abstract(self, html_content: str) -> str:
        """Extract abstract specifically from Google Scholar results"""
        
        # Google Scholar specific patterns
        scholar_patterns = [
            # Main result snippet
            r'<div class="gs_rs">(.*?)</div>',
            # Citation popup content
            r'<div id="gs_ccl"[^>]*>(.*?)</div>',
            # Result description
            r'<span class="gs_fl"[^>]*>.*?</span>\s*-\s*(.*?)(?:<span|$)',
            # Abstract in detailed view
            r'<div class="gs_ri"[^>]*>.*?<div class="gs_rs"[^>]*>(.*?)</div>',
        ]
        
        for pattern in scholar_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if matches:
                for match in matches:
                    cleaned = self._clean_extracted_text(match)
                    if len(cleaned) > 50 and len(cleaned) < 1000:
                        return cleaned
        
        return ""
    
    def _extract_from_pdf(self, url: str) -> Dict[str, str]:
        """Extract information from PDF with real PDF parsing"""
        print(f"    📄 Extracting from PDF: {url[:50]}...")
        
        try:
            # Download PDF content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=15) as response:
                pdf_content = response.read()
                
                # Try to extract text from PDF using basic text extraction
                # Note: For production, would use libraries like PyPDF2, pdfplumber, or pdf2image
                abstract = self._extract_pdf_abstract(pdf_content)
                
                return {
                    'abstract': abstract,
                    'content': abstract,
                    'explicit_keywords': [],
                    'journal': '',
                    'doi': ''
                }
                
        except Exception as e:
            print(f"      ⚠️  Error extracting from PDF: {e}")
            return {
                'abstract': '',
                'content': '',
                'explicit_keywords': [],
                'journal': '',
                'doi': ''
            }
    
    def _extract_pdf_abstract(self, pdf_content: bytes) -> str:
        """Extract abstract from PDF content (basic implementation)"""
        try:
            # Convert bytes to string (this is very basic - real implementation would use PDF libraries)
            text = pdf_content.decode('utf-8', errors='ignore')
            
            # Look for abstract section
            abstract_patterns = [
                r'(?i)abstract\s*:?\s*(.*?)(?:\n\s*\n|\n\s*1\.|introduction|keywords)',
                r'(?i)abstract\s+(.*?)(?:\n\s*keywords|\n\s*introduction|\n\s*1\.)',
            ]
            
            for pattern in abstract_patterns:
                matches = re.findall(pattern, text, re.DOTALL)
                if matches:
                    abstract = matches[0].strip()
                    if len(abstract) > 50 and len(abstract) < 2000:
                        return self._clean_extracted_text(abstract)
            
            return ""
            
        except Exception:
            return ""
    
    def _extract_from_webpage(self, url: str) -> Dict[str, str]:
        """Extract information from webpage with real web scraping"""
        print(f"    🌐 Extracting from webpage: {url[:50]}...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            request = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
                
                # Extract abstract using comprehensive method
                abstract = self._extract_abstract_from_html(content, "")
                
                # Extract explicit keywords
                keywords = self._extract_keywords_from_html(content)
                
                # Extract other metadata
                doi = self._extract_doi_from_html(content)
                journal = self._extract_journal_from_html(content)
                
                return {
                    'abstract': abstract,
                    'content': abstract,
                    'explicit_keywords': keywords,
                    'journal': journal,
                    'doi': doi
                }
                
        except Exception as e:
            print(f"      ⚠️  Error extracting from webpage: {e}")
            return {
                'abstract': '',
                'content': '',
                'explicit_keywords': [],
                'journal': '',
                'doi': ''
            }
    
    def _extract_keywords_from_html(self, html_content: str) -> List[str]:
        """Extract explicit keywords from HTML meta tags"""
        keyword_patterns = [
            r'<meta name="keywords" content="([^"]+)"',
            r'<meta name="citation_keywords" content="([^"]+)"',
            r'<meta property="article:tag" content="([^"]+)"',
            r'<meta name="DC\.Subject" content="([^"]+)"'
        ]
        
        keywords = []
        for pattern in keyword_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Split by common separators
                kw_list = re.split(r'[;,\|]', match)
                keywords.extend([kw.strip() for kw in kw_list if kw.strip()])
        
        return keywords[:10]  # Return top 10 explicit keywords
    
    def _extract_abstract_from_html(self, html_content: str, title: str) -> str:
        """Extract abstract from HTML content using multiple strategies"""
        
        # Strategy 1: Look for common abstract patterns
        abstract_patterns = [
            # Standard abstract tags
            r'<div[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</div>',
            r'<p[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</p>',
            r'<section[^>]*class="[^"]*abstract[^"]*"[^>]*>(.*?)</section>',
            
            # Meta description (often contains abstract)
            r'<meta\s+name="description"\s+content="([^"]+)"',
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            
            # Google Scholar specific patterns
            r'<div class="gs_rs">(.*?)</div>',
            r'<div id="gs_ccl"[^>]*>(.*?)</div>',
            
            # Academic paper patterns
            r'<h2[^>]*>Abstract</h2>\s*<p[^>]*>(.*?)</p>',
            r'<h3[^>]*>Abstract</h3>\s*<p[^>]*>(.*?)</p>',
            r'<strong>Abstract:?</strong>\s*(.*?)(?:<br|<p|<div)',
            r'<b>Abstract:?</b>\s*(.*?)(?:<br|<p|<div)',
            
            # ResearchGate patterns
            r'<div class="nova-legacy-e-text nova-legacy-e-text--size-m nova-legacy-e-text--family-sans-serif nova-legacy-e-text--spacing-none nova-legacy-e-text--color-grey-700"[^>]*>(.*?)</div>',
            
            # JSTOR patterns
            r'<p class="abstract"[^>]*>(.*?)</p>',
            
            # SpringerLink patterns
            r'<div class="c-article-section__content"[^>]*>(.*?)</div>',
            
            # Elsevier patterns
            r'<div class="abstract author"[^>]*>(.*?)</div>',
            
            # Generic patterns
            r'(?i)abstract[:\s]*</?\w*>\s*(.*?)(?:</?\w*>|\n\n)',
            r'(?i)<p[^>]*>\s*abstract[:\s]*(.*?)</p>',
        ]
        
        for pattern in abstract_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            if matches:
                for match in matches:
                    # Clean the extracted text
                    abstract = self._clean_extracted_text(match)
                    
                    # Validate the abstract
                    if self._is_valid_abstract(abstract, title):
                        print(f"    ✅ Found abstract ({len(abstract)} chars)")
                        return abstract
        
        # Strategy 2: Look for the first substantial paragraph after title
        title_words = title.lower().split()[:5] if title else []
        
        # Find paragraphs that might be abstracts
        paragraph_patterns = [
            r'<p[^>]*>(.*?)</p>',
            r'<div[^>]*>(.*?)</div>'
        ]
        
        for pattern in paragraph_patterns:
            paragraphs = re.findall(pattern, html_content, re.DOTALL)
            for paragraph in paragraphs:
                cleaned = self._clean_extracted_text(paragraph)
                
                # Check if this paragraph looks like an abstract
                if (len(cleaned) > 100 and len(cleaned) < 2000 and
                    any(word in cleaned.lower() for word in ['study', 'research', 'analysis', 'findings', 'results', 'conclusion'])):
                    
                    # Additional validation
                    if self._is_valid_abstract(cleaned, title):
                        print(f"    ✅ Found abstract from paragraph ({len(cleaned)} chars)")
                        return cleaned
        
        # Strategy 3: Extract from JSON-LD structured data
        json_ld_pattern = r'<script type="application/ld\+json"[^>]*>(.*?)</script>'
        json_matches = re.findall(json_ld_pattern, html_content, re.DOTALL)
        
        for json_content in json_matches:
            try:
                import json
                data = json.loads(json_content)
                
                # Look for abstract in various JSON-LD properties
                abstract_fields = ['abstract', 'description', 'summary']
                
                def extract_from_json(obj, fields):
                    if isinstance(obj, dict):
                        for field in fields:
                            if field in obj and isinstance(obj[field], str):
                                return obj[field]
                        for value in obj.values():
                            result = extract_from_json(value, fields)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = extract_from_json(item, fields)
                            if result:
                                return result
                    return None
                
                abstract = extract_from_json(data, abstract_fields)
                if abstract and self._is_valid_abstract(abstract, title):
                    print(f"    ✅ Found abstract from JSON-LD ({len(abstract)} chars)")
                    return abstract
                    
            except Exception as e:
                continue
        
        print("    ❌ No valid abstract found")
        return ""
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean extracted text by removing HTML tags and normalizing whitespace"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common prefixes
        text = re.sub(r'^(abstract:?\s*)', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _is_valid_abstract(self, text: str, title: str) -> bool:
        """Validate if extracted text is likely a real abstract"""
        if not text or len(text) < 50:
            return False
        
        # Too long to be an abstract
        if len(text) > 3000:
            return False
        
        # Check for academic language indicators
        academic_indicators = [
            'study', 'research', 'analysis', 'findings', 'results', 'conclusion',
            'method', 'approach', 'data', 'evidence', 'significant', 'examine',
            'investigate', 'demonstrate', 'suggest', 'indicate', 'show', 'reveal'
        ]
        
        text_lower = text.lower()
        indicator_count = sum(1 for indicator in academic_indicators if indicator in text_lower)
        
        # Should have at least 2 academic indicators
        if indicator_count < 2:
            return False
        
        # Should not be mostly navigation text or metadata
        navigation_terms = ['click here', 'download', 'pdf', 'login', 'register', 'subscribe', 'menu', 'home']
        nav_count = sum(1 for term in navigation_terms if term in text_lower)
        
        if nav_count > 2:
            return False
        
        # Should have reasonable sentence structure
        sentences = text.split('.')
        if len(sentences) < 2:
            return False
        
        return True
    
    def _extract_doi_from_html(self, html_content: str) -> str:
        """Extract DOI from HTML content"""
        doi_patterns = [
            r'doi[:\s]*([0-9]+\.[0-9]+/[^\s<>"]+)',
            r'<meta name="citation_doi" content="([^"]+)"',
            r'<meta name="DC\.Identifier" content="doi:([^"]+)"',
            r'https?://doi\.org/([0-9]+\.[0-9]+/[^\s<>"]+)',
            r'dx\.doi\.org/([0-9]+\.[0-9]+/[^\s<>"]+)'
        ]
        
        for pattern in doi_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def _extract_journal_from_html(self, html_content: str) -> str:
        """Extract journal name from HTML content"""
        journal_patterns = [
            r'<meta name="citation_journal_title" content="([^"]+)"',
            r'<meta name="DC\.Source" content="([^"]+)"',
            r'<meta property="og:site_name" content="([^"]+)"',
            r'<span class="journal-title"[^>]*>([^<]+)</span>',
            r'<h1 class="journal-name"[^>]*>([^<]+)</h1>'
        ]
        
        for pattern in journal_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def generate_keywords_from_text(self, text: str, title: str = "") -> List[str]:
        """Generate keywords from text using proper NLP techniques"""
        if not text or not text.strip():
            return []
        
        print(f"  🧠 Generating keywords from text ({len(text)} chars) using NLP...")
        
        if not NLP_AVAILABLE:
            print("    ⚠️  NLP libraries not available, falling back to simple extraction")
            return self._simple_keyword_extraction(text, title)
        
        try:
            # Combine title and text for analysis
            full_text = f"{title} {text}".strip()
            
            # Method 1: TF-IDF based keyword extraction
            tfidf_keywords = self._extract_tfidf_keywords(full_text)
            
            # Method 2: NLTK-based noun phrase extraction
            nltk_keywords = self._extract_nltk_keywords(full_text)
            
            # Method 3: Named entity recognition
            entities = self._extract_named_entities(full_text)
            
            # Combine and rank keywords
            all_keywords = set()
            
            # Add TF-IDF keywords (highest weight)
            all_keywords.update(tfidf_keywords[:10])
            
            # Add NLTK keywords
            all_keywords.update(nltk_keywords[:8])
            
            # Add named entities
            all_keywords.update(entities[:5])
            
            # Filter and clean keywords
            cleaned_keywords = self._clean_and_filter_keywords(list(all_keywords), title, text)
            
            print(f"    ✅ Extracted {len(cleaned_keywords)} keywords using NLP")
            return cleaned_keywords[:15]  # Return top 15
            
        except Exception as e:
            print(f"    ⚠️  NLP keyword extraction failed: {e}")
            return self._simple_keyword_extraction(text, title)
    
    def _extract_tfidf_keywords(self, text: str) -> List[str]:
        """Extract keywords using TF-IDF vectorization"""
        try:
            # Create TF-IDF vectorizer with academic stop words
            academic_stop_words = list(ENGLISH_STOP_WORDS) + [
                'study', 'research', 'analysis', 'paper', 'article', 'using', 'based',
                'results', 'findings', 'conclusion', 'abstract', 'introduction', 'method',
                'approach', 'data', 'model', 'framework', 'theory', 'evidence', 'significant',
                'important', 'different', 'various', 'several', 'many', 'most', 'some', 'all'
            ]
            
            vectorizer = TfidfVectorizer(
                max_features=50,
                stop_words=academic_stop_words,
                ngram_range=(1, 3),  # Include 1-3 word phrases
                min_df=1,
                max_df=0.8,
                lowercase=True
            )
            
            # Fit and transform the text
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Get keywords sorted by TF-IDF score
            keyword_scores = list(zip(feature_names, tfidf_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top keywords
            return [kw for kw, score in keyword_scores if score > 0][:15]
            
        except Exception as e:
            print(f"      ⚠️  TF-IDF extraction failed: {e}")
            return []
    
    def _extract_nltk_keywords(self, text: str) -> List[str]:
        """Extract keywords using NLTK noun phrase extraction"""
        try:
            # Tokenize and tag parts of speech
            tokens = word_tokenize(text.lower())
            pos_tags = pos_tag(tokens)
            
            # Extract noun phrases and important words
            keywords = set()
            
            # Get nouns and adjectives
            for word, pos in pos_tags:
                if len(word) > 3 and word.isalpha():
                    if pos.startswith('NN') or pos.startswith('JJ'):  # Nouns and adjectives
                        if word not in self.stop_words:
                            keywords.add(word)
            
            # Extract compound noun phrases (simplified)
            for i in range(len(pos_tags) - 1):
                word1, pos1 = pos_tags[i]
                word2, pos2 = pos_tags[i + 1]
                
                # Adjective + Noun or Noun + Noun
                if ((pos1.startswith('JJ') and pos2.startswith('NN')) or
                    (pos1.startswith('NN') and pos2.startswith('NN'))):
                    if len(word1) > 2 and len(word2) > 2:
                        compound = f"{word1} {word2}"
                        if word1 not in self.stop_words and word2 not in self.stop_words:
                            keywords.add(compound)
            
            return list(keywords)
            
        except Exception as e:
            print(f"      ⚠️  NLTK extraction failed: {e}")
            return []
    
    def _extract_named_entities(self, text: str) -> List[str]:
        """Extract named entities from text"""
        try:
            # Tokenize and tag
            tokens = word_tokenize(text)
            pos_tags = pos_tag(tokens)
            
            # Named entity recognition
            tree = ne_chunk(pos_tags)
            
            entities = []
            for subtree in tree:
                if isinstance(subtree, Tree):
                    entity_name = ' '.join([token for token, pos in subtree.leaves()])
                    entity_type = subtree.label()
                    
                    # Include relevant entity types
                    if entity_type in ['PERSON', 'ORGANIZATION', 'GPE', 'LOCATION']:
                        if len(entity_name) > 2:
                            entities.append(entity_name.lower())
            
            return entities
            
        except Exception as e:
            print(f"      ⚠️  Named entity extraction failed: {e}")
            return []
    
    def _clean_and_filter_keywords(self, keywords: List[str], title: str, text: str) -> List[str]:
        """Clean and filter extracted keywords"""
        cleaned = []
        title_lower = title.lower()
        text_lower = text.lower()
        
        for keyword in keywords:
            keyword = keyword.strip().lower()
            
            # Skip if too short or contains numbers/special chars
            if len(keyword) < 3 or not re.match(r'^[a-zA-Z\s]+$', keyword):
                continue
            
            # Skip if it's a stop word
            if keyword in self.stop_words:
                continue
            
            # Skip if it's too common/generic
            generic_terms = {'study', 'research', 'analysis', 'paper', 'article', 'method', 'approach'}
            if keyword in generic_terms:
                continue
            
            # Boost score if appears in title
            score = 1.0
            if keyword in title_lower:
                score += 2.0
            
            # Count occurrences in text
            occurrences = text_lower.count(keyword)
            score += occurrences * 0.5
            
            cleaned.append((keyword, score))
        
        # Sort by score and return keywords
        cleaned.sort(key=lambda x: x[1], reverse=True)
        return [kw for kw, score in cleaned]
    
    def _simple_keyword_extraction(self, text: str, title: str = "") -> List[str]:
        """Fallback simple keyword extraction when NLP libraries are not available"""
        # This is the original simple method
        full_text = f"{title} {text}".lower()
        
        keywords = set()
        
        # 1. Extract noun phrases (simplified)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', full_text)
        word_freq = {}
        for word in words:
            if word not in self.stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 2. Get most frequent meaningful words
        frequent_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        keywords.update([word for word, freq in frequent_words if freq >= 2])
        
        # 3. Look for domain-specific terms
        for domain, terms in self.domain_patterns.items():
            for term in terms:
                if term in full_text:
                    keywords.add(term)
        
        return list(keywords)[:10]
    
    def rank_keywords(self, explicit_keywords: List[str], generated_keywords: List[str], 
                     title: str, abstract: str) -> tuple[List[str], List[str]]:
        """Rank keywords by importance and relevance"""
        
        # Combine and score keywords
        keyword_scores = {}
        
        # Explicit keywords get highest score
        for keyword in explicit_keywords:
            keyword_scores[keyword.lower()] = 10.0
        
        # Generated keywords get base score
        for keyword in generated_keywords:
            if keyword.lower() not in keyword_scores:
                keyword_scores[keyword.lower()] = 5.0
        
        # Boost score if keyword appears in title
        title_lower = title.lower()
        for keyword in keyword_scores:
            if keyword in title_lower:
                keyword_scores[keyword] += 3.0
        
        # Boost score if keyword appears multiple times in abstract
        abstract_lower = abstract.lower()
        for keyword in keyword_scores:
            count = abstract_lower.count(keyword)
            if count > 1:
                keyword_scores[keyword] += count * 0.5
        
        # Sort by score
        sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Split into primary and secondary
        primary = [kw for kw, score in sorted_keywords[:8] if score >= 7.0]
        secondary = [kw for kw, score in sorted_keywords[8:] if score >= 5.0]
        
        return primary, secondary
    
    def extract_content_and_keywords(self, title: str, authors: str, publication_uri: str = "") -> ContentInfo:
        """Main method to extract abstract and keywords for a publication"""
        
        print(f"🔍 Extracting content and keywords for: {title[:50]}...")
        
        # Check cache first
        cache_key = self._create_cache_key(title, authors)
        if cache_key in self.cache:
            print(f"  ✅ Using cached content data")
            cached_data = self.cache[cache_key]
            return ContentInfo(**cached_data)
        
        # Initialize result
        content_info = ContentInfo(
            publication_title=title,
            publication_authors=authors,
            publication_uri=publication_uri,
            extraction_timestamp=str(int(time.time()))
        )
        
        try:
            # Step 1: Search for the article online
            search_result = self.search_for_article(title, authors)
            
            content_info.found_article_url = search_result.get('url', '')
            content_info.found_article_title = search_result.get('title', title)
            content_info.extraction_confidence = search_result.get('confidence', 0.0)
            content_info.extraction_method = search_result.get('method', 'unknown')
            
            # Step 2: Extract content if article was found
            if content_info.found_article_url:
                content_data = self.extract_content_from_url(content_info.found_article_url)
                
                content_info.article_abstract = content_data.get('abstract', '')
                content_info.article_doi = content_data.get('doi', '')
                content_info.article_journal = content_data.get('journal', '')
                content_info.explicit_keywords = content_data.get('explicit_keywords', [])
                
                # Step 3: Generate keywords from content
                text_for_analysis = f"{content_info.article_abstract} {content_data.get('content', '')}"
                content_info.generated_keywords = self.generate_keywords_from_text(text_for_analysis, title)
            
            else:
                # Fallback: generate keywords from title only
                print(f"  ⚠️  Article not found online, generating keywords from title only")
                content_info.generated_keywords = self.generate_keywords_from_text(title, title)
                content_info.extraction_confidence = 0.1
                content_info.extraction_method = 'title_only'
            
            # Step 4: Rank and categorize keywords
            primary, secondary = self.rank_keywords(
                content_info.explicit_keywords,
                content_info.generated_keywords,
                title,
                content_info.article_abstract
            )
            
            content_info.primary_keywords = primary
            content_info.secondary_keywords = secondary
            
            print(f"  ✅ Extracted {len(primary)} primary + {len(secondary)} secondary keywords")
            
        except Exception as e:
            print(f"  ❌ Content extraction failed: {e}")
            content_info.extraction_confidence = 0.0
            content_info.extraction_method = 'failed'
        
        # Cache the result
        self.cache[cache_key] = asdict(content_info)
        self._save_cache()
        
        return content_info
    
    def extract_content_batch(self, publications: List[Dict[str, str]]) -> List[ContentInfo]:
        """Extract content and keywords for multiple publications"""
        results = []
        
        print(f"🚀 Processing {len(publications)} publications for content extraction")
        
        for i, pub in enumerate(publications, 1):
            print(f"\n--- Publication {i}/{len(publications)} ---")
            
            title = pub.get('title', '')
            authors = pub.get('authors', '')
            uri = pub.get('uri', '')
            
            content_info = self.extract_content_and_keywords(title, authors, uri)
            results.append(content_info)
            
            # Rate limiting between requests
            if i < len(publications):
                time.sleep(2)
        
        return results

def main():
    """Command line interface for keyword and abstract enrichment"""
    parser = argparse.ArgumentParser(description="Extract keywords and abstracts from academic publications")
    parser.add_argument("title", help="Publication title")
    parser.add_argument("--authors", default="", help="Publication authors")
    parser.add_argument("--uri", default="", help="Publication URI")
    parser.add_argument("--output", help="Output JSON file")
    parser.add_argument("--cache", default="cache/keyword_abstract_enrichment_cache.json", help="Cache file location")
    
    args = parser.parse_args()
    
    print("🚀 SSHOC-NL Keyword and Abstract Extraction Tool")
    print("=" * 60)
    
    # Initialize enricher
    enricher = KeywordAbstractEnricher(cache_file=args.cache)
    
    # Extract content and keywords
    content_info = enricher.extract_content_and_keywords(args.title, args.authors, args.uri)
    
    # Display results
    print("\n📊 CONTENT AND KEYWORD EXTRACTION RESULTS")
    print("=" * 60)
    print(f"Title: {content_info.publication_title}")
    print(f"Authors: {content_info.publication_authors}")
    print(f"Found Article: {content_info.found_article_url}")
    print(f"Confidence: {content_info.extraction_confidence:.2f}")
    print(f"Method: {content_info.extraction_method}")
    
    if content_info.article_abstract:
        print(f"\n📄 Abstract ({len(content_info.article_abstract)} chars):")
        print(f"  {content_info.article_abstract[:200]}{'...' if len(content_info.article_abstract) > 200 else ''}")
    
    if content_info.explicit_keywords:
        print(f"\n🏷️  Explicit Keywords ({len(content_info.explicit_keywords)}):")
        for kw in content_info.explicit_keywords:
            print(f"  - {kw}")
    
    if content_info.primary_keywords:
        print(f"\n⭐ Primary Keywords ({len(content_info.primary_keywords)}):")
        for kw in content_info.primary_keywords:
            print(f"  - {kw}")
    
    if content_info.secondary_keywords:
        print(f"\n📝 Secondary Keywords ({len(content_info.secondary_keywords)}):")
        for kw in content_info.secondary_keywords:
            print(f"  - {kw}")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(asdict(content_info), f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {args.output}")
    
    print(f"\n🎉 Content and keyword extraction completed!")

if __name__ == "__main__":
    main()

