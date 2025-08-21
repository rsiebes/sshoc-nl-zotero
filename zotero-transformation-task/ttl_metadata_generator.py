#!/usr/bin/env python3
"""
TTL Metadata Generator for SSHOC-NL Zotero Pipeline

This script processes publications from original.ttl and generates enriched
Dublin Core BIBO-compliant metadata files with intelligent caching for
ELSST vocabulary and ORCID author information.

Usage:
    python3 ttl_metadata_generator.py [start_index] [end_index]
    
Examples:
    python3 ttl_metadata_generator.py 1 25    # Process first 25 publications
    python3 ttl_metadata_generator.py 26 50   # Process publications 26-50
    python3 ttl_metadata_generator.py         # Process all publications

Author: Ronald Siebes - UCDS group - VU Amsterdam
Date: July 2025
Version: 2.0.0
"""

import sys
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import author enrichment functionality
from author_enrichment import AuthorEnricher, AuthorInfo

@dataclass
class Publication:
    """Data class for publication information extracted from original.ttl"""
    uri: str
    title: str
    creators: List[str]
    date: str
    parent_organization: str
    index: int

class TTLParser:
    """Parser for extracting publication information from original.ttl"""
    
    def __init__(self, ttl_file_path: str):
        self.ttl_file_path = ttl_file_path
        self.publications = []
    
    def parse_publications(self) -> List[Publication]:
        """Parse all publications from the TTL file"""
        try:
            with open(self.ttl_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by publication URIs (lines starting with <http)
            publication_blocks = re.split(r'\n(?=<http)', content)
            
            for i, block in enumerate(publication_blocks):
                if block.strip() and '<http' in block:
                    pub = self._parse_publication_block(block, i + 1)
                    if pub:
                        self.publications.append(pub)
            
            print(f"✅ Parsed {len(self.publications)} publications from {self.ttl_file_path}")
            return self.publications
            
        except FileNotFoundError:
            print(f"❌ Error: Could not find {self.ttl_file_path}")
            return []
        except Exception as e:
            print(f"❌ Error parsing TTL file: {e}")
            return []
    
    def _parse_publication_block(self, block: str, index: int) -> Optional[Publication]:
        """Parse a single publication block"""
        try:
            lines = block.strip().split('\n')
            
            # Extract URI (first line)
            uri_match = re.match(r'<([^>]+)>', lines[0])
            if not uri_match:
                return None
            uri = uri_match.group(1)
            
            # Extract title
            title = self._extract_field(block, 'dc:title')
            if not title:
                title = f"Publication {index}"
            
            # Extract creators
            creators = self._extract_creators(block)
            
            # Extract date
            date = self._extract_field(block, 'dc:date') or "Unknown"
            
            # Extract parent organization
            parent_org = self._extract_field(block, 'ns0:parentOrganization') or "Unknown"
            
            return Publication(
                uri=uri,
                title=title,
                creators=creators,
                date=date,
                parent_organization=parent_org,
                index=index
            )
            
        except Exception as e:
            print(f"⚠️  Warning: Could not parse publication block {index}: {e}")
            return None
    
    def _extract_field(self, block: str, field_name: str) -> Optional[str]:
        """Extract a field value from a publication block"""
        pattern = rf'{field_name}\s+"([^"]+)"'
        match = re.search(pattern, block)
        return match.group(1) if match else None
    
    def _extract_creators(self, block: str) -> List[str]:
        """Extract creator names from a publication block"""
        creators = []
        creator_pattern = r'dc:creator\s+"([^"]+)"'
        matches = re.findall(creator_pattern, block)
        return matches

class MetadataEnricher:
    """Enriches publication metadata using cached information and author enrichment"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.orcid_cache = self._load_cache("orcid_cache.json")
        self.elsst_cache = self._load_cache("elsst_cache.json")
        self.org_cache = self._load_cache("organization_cache.json")
        
        # Initialize author enricher
        self.author_enricher = AuthorEnricher(cache_file=str(self.cache_dir / "author_enrichment_cache.json"))
    
    def _load_cache(self, filename: str) -> Dict:
        """Load cache file or return empty dict"""
        cache_file = self.cache_dir / filename
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Warning: Could not load {filename}: {e}")
        return {}
    
    def enrich_publication(self, pub: Publication) -> Tuple[str, str]:
        """Generate enriched TTL metadata for a publication with author enrichment"""
        print(f"🔍 Enriching publication: {pub.title[:50]}...")
        
        # Generate file ID
        file_id = self._generate_file_id(pub)
        
        # Enrich authors
        print(f"  👥 Enriching {len(pub.creators)} authors...")
        enriched_authors = []
        
        # Parse all authors from the creators string
        if pub.creators:
            authors_string = pub.creators[0] if len(pub.creators) == 1 else ", ".join(pub.creators)
            try:
                enriched_authors = self.author_enricher.enrich_authors_from_string(
                    authors_string, 
                    pub.title, 
                    pub.parent_organization
                )
            except Exception as e:
                print(f"    ⚠️ Error enriching authors: {e}")
                # Create basic author info as fallback
                for creator in pub.creators:
                    given_name, family_name = self.author_enricher.parse_author_name(creator)
                    fallback_author = AuthorInfo(
                        full_name=creator,
                        given_name=given_name,
                        family_name=family_name
                    )
                    enriched_authors.append(fallback_author)
        
        # Generate TTL content with enriched authors
        ttl_content = self._generate_enriched_ttl_content(pub, file_id, enriched_authors)
        
        print(f"  ✅ Generated enriched metadata for {file_id}")
        return ttl_content, file_id
    
    def _generate_file_id(self, pub: Publication) -> str:
        """Generate a unique file identifier"""
        # Extract meaningful parts from title or creators for filename
        if pub.creators:
            creator_part = pub.creators[0].split()[-1].upper()  # Last name of first author
        else:
            creator_part = "UNKNOWN"
        
        # Add organization part
        org_part = pub.parent_organization.replace(" ", "_").upper()[:10]
        
        # Create unique ID
        return f"{creator_part}_{org_part}_{pub.index:03d}"
    
    def _generate_enriched_ttl_content(self, pub: Publication, file_id: str, enriched_authors: List[AuthorInfo]) -> str:
        """Generate enriched TTL content for a publication with detailed author information"""
        
        # TTL prefixes
        ttl_content = """@prefix dc: <http://purl.org/dc/terms/> .
@prefix bibo: <http://purl.org/ontology/bibo/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix schema: <http://schema.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""
        
        # Main publication resource
        ttl_content += f"""<{pub.uri}>
    a bibo:Article, schema:ScholarlyArticle ;
    dc:title "{self._escape_ttl_string(pub.title)}" ;
    dc:date "{pub.date}"^^xsd:gYear ;
    dc:identifier "{file_id}" ;
    
    # Original URI preserved
    rdfs:seeAlso <{pub.uri}> ;
    
"""
        
        # Add enriched authors
        author_uris = []
        for i, author in enumerate(enriched_authors):
            author_uri = self.author_enricher.generate_author_uri(author)
            author_uris.append(author_uri)
            ttl_content += f"    schema:author <{author_uri}> ;\n"
        
        # Close main resource
        ttl_content += f"""    
    # Parent organization
    schema:parentOrganization [
        a foaf:Organization ;
        foaf:name "{self._escape_ttl_string(pub.parent_organization)}" ;
        dc:identifier "{pub.parent_organization}" ;
    ] ;
    
    # Producer information
    schema:producer <https://w3id.org/odissei/ns/kg/cbs/project/unknown> ;
    
    # Content classification
    bibo:status "Published" ;
    schema:genre "Academic research" ;
    
    # Temporal coverage
    schema:temporalCoverage "{pub.date}" ;
    schema:dateCreated "{pub.date}"^^xsd:gYear .

"""
        
        # Add detailed author information using the author enricher
        for i, author in enumerate(enriched_authors):
            author_uri = author_uris[i]
            author_ttl = self.author_enricher.generate_author_ttl(author, author_uri)
            ttl_content += author_ttl
        
        return ttl_content
    
    def _escape_ttl_string(self, text: str) -> str:
        """Escape special characters in TTL strings"""
        if not text:
            return ""
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

class TTLMetadataGenerator:
    """Main class for generating enriched metadata from original.ttl"""
    
    def __init__(self, data_dir: str = "data", cache_dir: str = "cache"):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.parser = TTLParser("data/original.ttl")
        self.enricher = MetadataEnricher(cache_dir)
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "generated").mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
    
    def process_publications(self, start_index: int = 1, end_index: Optional[int] = None) -> None:
        """Process publications from start_index to end_index"""
        
        # Parse publications from TTL file
        publications = self.parser.parse_publications()
        
        if not publications:
            print("❌ No publications found to process")
            return
        
        # Determine range
        if end_index is None:
            end_index = len(publications)
        
        # Validate range
        start_index = max(1, start_index)
        end_index = min(len(publications), end_index)
        
        if start_index > end_index:
            print(f"❌ Invalid range: start_index ({start_index}) > end_index ({end_index})")
            return
        
        print(f"🚀 Processing publications {start_index} to {end_index} of {len(publications)} total")
        
        # Process each publication in range
        processed_count = 0
        for i in range(start_index - 1, end_index):
            pub = publications[i]
            
            try:
                # Enrich metadata
                ttl_content, file_id = self.enricher.enrich_publication(pub)
                
                # Write TTL file
                output_file = self.data_dir / "generated" / f"{file_id}.ttl"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(ttl_content)
                
                processed_count += 1
                print(f"✅ [{processed_count:3d}/{end_index-start_index+1:3d}] Generated {file_id}.ttl")
                
            except Exception as e:
                print(f"❌ Error processing publication {i+1}: {e}")
        
        print(f"🎉 Successfully processed {processed_count} publications!")
        print(f"📁 Generated files saved to: {self.data_dir / 'generated'}")

def main():
    """Main function"""
    print("🔧 SSHOC-NL TTL Metadata Generator v2.0.0")
    print("=" * 50)
    
    # Parse command line arguments
    start_index = 1
    end_index = None
    
    if len(sys.argv) >= 2:
        try:
            start_index = int(sys.argv[1])
        except ValueError:
            print("❌ Error: start_index must be an integer")
            sys.exit(1)
    
    if len(sys.argv) >= 3:
        try:
            end_index = int(sys.argv[2])
        except ValueError:
            print("❌ Error: end_index must be an integer")
            sys.exit(1)
    
    # Check if original.ttl exists
    if not os.path.exists("data/original.ttl"):
        print("❌ Error: data/original.ttl not found")
        print("Please ensure original.ttl is in the data/ directory")
        sys.exit(1)
    
    # Create and run generator
    generator = TTLMetadataGenerator()
    generator.process_publications(start_index, end_index)

if __name__ == "__main__":
    main()

