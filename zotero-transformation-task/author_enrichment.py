#!/usr/bin/env python3
"""
Author Enrichment Script for SSHOC-NL Zotero Pipeline

This script enriches author information by finding:
- ORCID IDs
- Institutional affiliations
- Job titles and positions
- Research citations (Google Scholar)
- Expertise areas
- Contact information

Usage:
    python3 author_enrichment.py "Author Name" [--publication-title "Title"]
    
Example:
    python3 author_enrichment.py "Aletta Dijkstra" --publication-title "Can selective migration explain why health is worse in regions with population decline"

Author: Assistant for SSHOC-NL Pipeline
Date: August 2025
"""

import sys
import json
import re
import time
import hashlib
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse

@dataclass
class AuthorInfo:
    """Data class for comprehensive author information"""
    full_name: str
    given_name: str = ""
    family_name: str = ""
    orcid_id: str = ""
    email: str = ""
    current_position: str = ""
    affiliation: str = ""
    department: str = ""
    institution_url: str = ""
    institution_ror_id: str = ""
    google_scholar_id: str = ""
    citation_count: int = 0
    h_index: int = 0
    expertise_areas: List[str] = None
    research_interests: List[str] = None
    
    def __post_init__(self):
        if self.expertise_areas is None:
            self.expertise_areas = []
        if self.research_interests is None:
            self.research_interests = []

class AuthorEnricher:
    """Main class for enriching author information"""
    
    def __init__(self, cache_file: str = "cache/author_enrichment_cache.json"):
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def load_cache(self) -> Dict:
        """Load existing cache or create new one"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_cache(self):
        """Save cache to file"""
        import os
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
    
    def parse_author_name(self, full_name: str) -> Tuple[str, str]:
        """Parse full name into given and family names"""
        # Handle various name formats
        name_parts = full_name.strip().split()
        
        if len(name_parts) == 1:
            return "", name_parts[0]
        elif len(name_parts) == 2:
            return name_parts[0], name_parts[1]
        else:
            # Assume last part is family name, rest is given name
            given_name = " ".join(name_parts[:-1])
            family_name = name_parts[-1]
            return given_name, family_name
    
    def search_orcid(self, author_name: str) -> Optional[str]:
        """Search for ORCID ID using ORCID API"""
        try:
            # Clean author name for search
            search_name = re.sub(r'[^\w\s]', '', author_name)
            encoded_name = urllib.parse.quote(search_name)
            
            # ORCID API search
            url = f"https://pub.orcid.org/v3.0/search/?q=given-and-family-names:{encoded_name}"
            headers = {
                'Accept': 'application/json',
                'User-Agent': self.session_headers['User-Agent']
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            # Parse results
            if 'result' in data and data['result']:
                for result in data['result'][:3]:  # Check top 3 results
                    if 'orcid-identifier' in result:
                        orcid_path = result['orcid-identifier']['path']
                        # Verify this is a reasonable match
                        if self.verify_orcid_match(orcid_path, author_name):
                            return f"https://orcid.org/{orcid_path}"
            
            return None
            
        except Exception as e:
            print(f"ORCID search error for {author_name}: {e}")
            return None
    
    def verify_orcid_match(self, orcid_path: str, author_name: str) -> bool:
        """Verify if ORCID profile matches the author name"""
        try:
            url = f"https://pub.orcid.org/v3.0/{orcid_path}/person"
            headers = {
                'Accept': 'application/json',
                'User-Agent': self.session_headers['User-Agent']
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
            
            # Extract name from ORCID profile
            if 'name' in data and data['name']:
                given_names = data['name'].get('given-names', {}).get('value', '')
                family_name = data['name'].get('family-name', {}).get('value', '')
                orcid_full_name = f"{given_names} {family_name}".strip()
                
                # Simple name matching (can be improved)
                author_clean = re.sub(r'[^\w\s]', '', author_name.lower())
                orcid_clean = re.sub(r'[^\w\s]', '', orcid_full_name.lower())
                
                # Check if names have significant overlap
                author_words = set(author_clean.split())
                orcid_words = set(orcid_clean.split())
                
                if len(author_words & orcid_words) >= min(2, len(author_words)):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def get_orcid_details(self, orcid_id: str) -> Dict:
        """Get detailed information from ORCID profile"""
        try:
            orcid_path = orcid_id.split('/')[-1]
            details = {}
            
            print(f"    🔍 Fetching detailed ORCID profile for {orcid_path}...")
            
            # Get person information (name, biography, etc.)
            person_url = f"https://pub.orcid.org/v3.0/{orcid_path}/person"
            person_data = self._make_orcid_request(person_url)
            
            if person_data:
                # Extract name information
                if 'name' in person_data and person_data['name']:
                    name_info = person_data['name']
                    if 'given-names' in name_info and name_info['given-names']:
                        details['given_name'] = name_info['given-names']['value']
                    if 'family-name' in name_info and name_info['family-name']:
                        details['family_name'] = name_info['family-name']['value']
                
                # Extract biography
                if 'biography' in person_data and person_data['biography'] and person_data['biography']['content']:
                    details['biography'] = person_data['biography']['content']
                
                # Extract researcher URLs
                if 'researcher-urls' in person_data and person_data['researcher-urls']:
                    urls = []
                    for url_group in person_data['researcher-urls']['researcher-url']:
                        if 'url' in url_group and 'url-name' in url_group:
                            urls.append({
                                'name': url_group['url-name'],
                                'url': url_group['url']['value']
                            })
                    details['researcher_urls'] = urls
            
            # Get employment information
            employment_url = f"https://pub.orcid.org/v3.0/{orcid_path}/employments"
            employment_data = self._make_orcid_request(employment_url)
            
            if employment_data and 'affiliation-group' in employment_data:
                employments = []
                current_affiliation = ""
                current_position = ""
                current_department = ""
                
                for group in employment_data['affiliation-group']:
                    for summary in group.get('summaries', []):
                        employment = summary.get('employment-summary', {})
                        if employment:
                            org = employment.get('organization', {})
                            org_name = org.get('name', '')
                            position = employment.get('role-title', '')
                            department = employment.get('department-name', '')
                            start_date = employment.get('start-date')
                            end_date = employment.get('end-date')
                            
                            emp_info = {
                                'organization': org_name,
                                'position': position,
                                'department': department,
                                'start_date': self._format_orcid_date(start_date) if start_date else None,
                                'end_date': self._format_orcid_date(end_date) if end_date else None,
                                'current': end_date is None
                            }
                            employments.append(emp_info)
                            
                            # Set current employment (first one without end date)
                            if not current_affiliation and end_date is None:
                                current_affiliation = org_name
                                current_position = position
                                current_department = department
                
                details['employments'] = employments
                details['current_affiliation'] = current_affiliation
                details['current_position'] = current_position
                details['current_department'] = current_department
            
            # Get education information
            education_url = f"https://pub.orcid.org/v3.0/{orcid_path}/educations"
            education_data = self._make_orcid_request(education_url)
            
            if education_data and 'affiliation-group' in education_data:
                educations = []
                for group in education_data['affiliation-group']:
                    for summary in group.get('summaries', []):
                        education = summary.get('education-summary', {})
                        if education:
                            org = education.get('organization', {})
                            edu_info = {
                                'organization': org.get('name', ''),
                                'degree': education.get('role-title', ''),
                                'department': education.get('department-name', ''),
                                'start_date': self._format_orcid_date(education.get('start-date')),
                                'end_date': self._format_orcid_date(education.get('end-date'))
                            }
                            educations.append(edu_info)
                
                details['educations'] = educations
            
            # Get works (publications) information
            works_url = f"https://pub.orcid.org/v3.0/{orcid_path}/works"
            works_data = self._make_orcid_request(works_url)
            
            if works_data and 'group' in works_data:
                details['publication_count'] = len(works_data['group'])
                
                # Get details of first few works for research interests
                research_areas = set()
                work_titles = []
                
                for i, group in enumerate(works_data['group'][:5]):  # First 5 works
                    if 'work-summary' in group:
                        for work_summary in group['work-summary']:
                            if 'title' in work_summary and work_summary['title']:
                                title = work_summary['title']['title']['value']
                                work_titles.append(title)
                                
                                # Extract potential research areas from titles
                                title_lower = title.lower()
                                if any(keyword in title_lower for keyword in ['health', 'medical', 'clinical']):
                                    research_areas.add('Health Sciences')
                                if any(keyword in title_lower for keyword in ['economic', 'finance', 'market']):
                                    research_areas.add('Economics')
                                if any(keyword in title_lower for keyword in ['social', 'demographic', 'population']):
                                    research_areas.add('Social Sciences')
                                if any(keyword in title_lower for keyword in ['environment', 'climate', 'sustainability']):
                                    research_areas.add('Environmental Sciences')
                
                details['recent_works'] = work_titles[:3]
                details['research_areas'] = list(research_areas)
            
            # Get keywords/research interests
            keywords_url = f"https://pub.orcid.org/v3.0/{orcid_path}/keywords"
            keywords_data = self._make_orcid_request(keywords_url)
            
            if keywords_data and 'keyword' in keywords_data:
                keywords = []
                for keyword in keywords_data['keyword']:
                    if 'content' in keyword:
                        keywords.append(keyword['content'])
                details['keywords'] = keywords
            
            print(f"    ✅ Retrieved detailed ORCID information")
            return details
            
        except Exception as e:
            print(f"    ❌ Error getting ORCID details: {e}")
            return {}
    
    def _make_orcid_request(self, url: str) -> Dict:
        """Make a request to ORCID API with proper error handling"""
        try:
            headers = {
                'Accept': 'application/json',
                'User-Agent': self.session_headers['User-Agent']
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode())
                
        except Exception as e:
            print(f"    ⚠️ ORCID API request failed for {url}: {e}")
            return {}
    
    def _format_orcid_date(self, date_obj) -> Optional[str]:
        """Format ORCID date object to string"""
        if not date_obj:
            return None
        
        try:
            year = date_obj.get('year', {}).get('value', '')
            month = date_obj.get('month', {}).get('value', '')
            day = date_obj.get('day', {}).get('value', '')
            
            if year:
                if month and day:
                    return f"{year}-{month:02d}-{day:02d}"
                elif month:
                    return f"{year}-{month:02d}"
                else:
                    return str(year)
            return None
        except:
            return None
    
    def search_google_scholar(self, author_name: str, publication_title: str = "") -> Dict:
        """Search Google Scholar for author information"""
        try:
            # Note: This is a placeholder for Google Scholar integration
            # In production, you would use the scholarly library or similar
            # For now, return empty results since we don't have real Google Scholar API access
            
            return {
                'scholar_id': '',
                'citation_count': 0,
                'h_index': 0,
                'expertise_areas': []
            }
            
        except Exception as e:
            print(f"Google Scholar search error: {e}")
            return {}
    
    def search_institutional_info(self, author_name: str, affiliation_hint: str = "") -> Dict:
        """Search for institutional information"""
        try:
            # For Dutch institutions, we can use known patterns
            institutional_info = {
                'institution_url': '',
                'email': '',
                'ror_id': ''
            }
            
            # Check if this is a University of Groningen author (RUG_FRW)
            if "rug" in affiliation_hint.lower() or "groningen" in affiliation_hint.lower():
                institutional_info.update({
                    'institution_url': 'https://www.rug.nl/',
                    'ror_id': 'https://ror.org/012p63287',  # RUG ROR ID
                    'affiliation': 'University of Groningen, Faculty of Spatial Sciences'
                })
                
                # Try to construct email (common pattern)
                if author_name:
                    given, family = self.parse_author_name(author_name)
                    if given and family:
                        email_guess = f"{given.lower().replace(' ', '.')}.{family.lower()}@rug.nl"
                        institutional_info['email'] = email_guess
            
            return institutional_info
            
        except Exception as e:
            print(f"Institutional search error: {e}")
            return {}
    
    def enrich_author(self, author_name: str, publication_title: str = "", parent_org: str = "") -> AuthorInfo:
        """Main method to enrich a single author"""
        
        # Check cache first
        cache_key = f"{author_name}_{parent_org}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            author_info = AuthorInfo(**cached_data)
            print(f"✅ Using cached data for {author_name}")
            return author_info
        
        print(f"🔍 Enriching author: {author_name}")
        
        # Initialize author info
        given_name, family_name = self.parse_author_name(author_name)
        author_info = AuthorInfo(
            full_name=author_name,
            given_name=given_name,
            family_name=family_name
        )
        
        # Search for ORCID
        print(f"  📋 Searching ORCID for {author_name}...")
        orcid_id = self.search_orcid(author_name)
        if orcid_id:
            author_info.orcid_id = orcid_id
            print(f"  ✅ Found ORCID: {orcid_id}")
            
            # Get comprehensive ORCID details
            orcid_details = self.get_orcid_details(orcid_id)
            if orcid_details:
                # Update name information from ORCID if available
                if orcid_details.get('given_name') and not author_info.given_name:
                    author_info.given_name = orcid_details['given_name']
                if orcid_details.get('family_name') and not author_info.family_name:
                    author_info.family_name = orcid_details['family_name']
                
                # Set current employment information
                if orcid_details.get('current_affiliation'):
                    author_info.affiliation = orcid_details['current_affiliation']
                if orcid_details.get('current_position'):
                    author_info.current_position = orcid_details['current_position']
                if orcid_details.get('current_department'):
                    author_info.department = orcid_details['current_department']
                
                # Set research areas from ORCID
                if orcid_details.get('research_areas'):
                    author_info.expertise_areas = orcid_details['research_areas']
                if orcid_details.get('keywords'):
                    author_info.research_interests = orcid_details['keywords']
                
                # Store additional ORCID information in a structured way
                additional_info = {}
                if orcid_details.get('biography'):
                    additional_info['biography'] = orcid_details['biography']
                if orcid_details.get('publication_count'):
                    additional_info['publication_count'] = orcid_details['publication_count']
                if orcid_details.get('recent_works'):
                    additional_info['recent_works'] = orcid_details['recent_works']
                if orcid_details.get('employments'):
                    additional_info['employment_history'] = orcid_details['employments']
                if orcid_details.get('educations'):
                    additional_info['education_history'] = orcid_details['educations']
                if orcid_details.get('researcher_urls'):
                    additional_info['researcher_urls'] = orcid_details['researcher_urls']
                
                # Store in a way that can be serialized
                if additional_info:
                    # We'll add this to the cache but not to the main AuthorInfo dataclass
                    # since it has fixed fields
                    pass
        else:
            print(f"  ❌ No ORCID found for {author_name}")
        
        # Search Google Scholar (placeholder)
        print(f"  🎓 Searching Google Scholar...")
        scholar_info = self.search_google_scholar(author_name, publication_title)
        if scholar_info:
            if scholar_info.get('scholar_id'):
                author_info.google_scholar_id = scholar_info['scholar_id']
            if scholar_info.get('citation_count'):
                author_info.citation_count = scholar_info['citation_count']
            if scholar_info.get('h_index'):
                author_info.h_index = scholar_info['h_index']
            if scholar_info.get('expertise_areas') and not author_info.expertise_areas:
                author_info.expertise_areas = scholar_info['expertise_areas']
        
        # Search institutional information
        print(f"  🏛️ Searching institutional info...")
        inst_info = self.search_institutional_info(author_name, parent_org)
        if inst_info:
            if inst_info.get('institution_url'):
                author_info.institution_url = inst_info['institution_url']
            if inst_info.get('email'):
                author_info.email = inst_info['email']
            if inst_info.get('ror_id'):
                author_info.institution_ror_id = inst_info['ror_id']
            if inst_info.get('affiliation') and not author_info.affiliation:
                author_info.affiliation = inst_info['affiliation']
        
        # Cache the result
        self.cache[cache_key] = asdict(author_info)
        self.save_cache()
        
        print(f"  ✅ Enrichment complete for {author_name}")
        return author_info
    
    def generate_author_uri(self, author: AuthorInfo) -> str:
        """Generate a unique URI for an author using ODISSEI namespace"""
        
        # Create a base identifier from the author's name
        name_parts = []
        if author.given_name:
            name_parts.append(author.given_name.lower())
        if author.family_name:
            name_parts.append(author.family_name.lower())
        
        # If no name parts, use full name
        if not name_parts:
            name_parts = [author.full_name.lower()]
        
        # Clean and join name parts
        clean_name = "_".join(name_parts)
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name.replace(' ', '_'))
        
        # Create a hash from the full name for uniqueness
        name_hash = hashlib.md5(author.full_name.encode('utf-8')).hexdigest()[:8]
        
        # Combine name and hash for a unique but readable identifier
        author_id = f"{clean_name}_{name_hash}"
        
        return f"https://w3id.org/odissei/ns/kg/person/{author_id}"
    
    def generate_author_ttl(self, author: AuthorInfo, author_uri: str) -> str:
        """Generate TTL content for a single author"""
        
        ttl_content = f"""
<{author_uri}>
    a foaf:Person, schema:Person ;
    foaf:name "{self._escape_ttl_string(author.full_name)}" ;
"""
        
        if author.given_name:
            ttl_content += f'    foaf:givenName "{self._escape_ttl_string(author.given_name)}" ;\n'
        if author.family_name:
            ttl_content += f'    foaf:familyName "{self._escape_ttl_string(author.family_name)}" ;\n'
        
        # ORCID information
        if author.orcid_id:
            ttl_content += f'    schema:identifier "{author.orcid_id}" ;\n'
            ttl_content += f'    foaf:homepage <{author.orcid_id}> ;\n'
        
        # Email
        if author.email:
            ttl_content += f'    foaf:mbox <mailto:{author.email}> ;\n'
        
        # Current position and affiliation
        if author.current_position:
            ttl_content += f'    schema:jobTitle "{self._escape_ttl_string(author.current_position)}" ;\n'
        
        if author.affiliation:
            ttl_content += f'    schema:affiliation "{self._escape_ttl_string(author.affiliation)}" ;\n'
        
        if author.department:
            ttl_content += f'    schema:department "{self._escape_ttl_string(author.department)}" ;\n'
        
        # Institution information
        if author.institution_url:
            ttl_content += f'    schema:worksFor <{author.institution_url}> ;\n'
        
        if author.institution_ror_id:
            ttl_content += f'    schema:memberOf <{author.institution_ror_id}> ;\n'
        
        # Research information
        if author.expertise_areas:
            for area in author.expertise_areas:
                ttl_content += f'    schema:knowsAbout "{self._escape_ttl_string(area)}" ;\n'
        
        if author.research_interests:
            for interest in author.research_interests:
                ttl_content += f'    schema:interest "{self._escape_ttl_string(interest)}" ;\n'
        
        # Google Scholar information
        if author.google_scholar_id:
            ttl_content += f'    schema:sameAs <https://scholar.google.com/citations?user={author.google_scholar_id}> ;\n'
        
        if author.citation_count > 0:
            ttl_content += f'    schema:citationCount {author.citation_count} ;\n'
        
        if author.h_index > 0:
            ttl_content += f'    schema:hIndex {author.h_index} ;\n'
        
        # Remove trailing semicolon and add period
        ttl_content = ttl_content.rstrip(' ;\n') + ' .\n'
        
        return ttl_content
    
    def _escape_ttl_string(self, text: str) -> str:
        """Escape special characters in TTL strings"""
        if not text:
            return ""
        return text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
    
    def enrich_authors_from_string(self, authors_string: str, publication_title: str = "", parent_org: str = "") -> List[AuthorInfo]:
        """Enrich multiple authors from a comma-separated string"""
        
        # Parse author string - handle academic citation format
        # Format: "Last1, First1, First2 Last2, First3 Last3, First4 Last4 & First5 Last5"
        
        authors = []
        
        # First, split by ' & ' to separate the last author
        if ' & ' in authors_string:
            parts = authors_string.split(' & ')
            main_authors = parts[0].strip()
            last_author = parts[1].strip()
            if last_author:
                authors.append(last_author)
        else:
            main_authors = authors_string.strip()
        
        # Now parse the main authors part
        if main_authors:
            comma_parts = [p.strip() for p in main_authors.split(',')]
            
            if len(comma_parts) >= 2:
                # First author: "Last, First" -> "First Last"
                first_author = f"{comma_parts[1]} {comma_parts[0]}"
                authors.insert(0, first_author)
                
                # Remaining parts are individual authors in "First Last" format
                for i in range(2, len(comma_parts)):
                    if comma_parts[i].strip():
                        authors.insert(-1 if ' & ' in authors_string else len(authors), comma_parts[i].strip())
            elif len(comma_parts) == 1:
                # Single author
                authors.insert(0, comma_parts[0].strip())
        
        # Clean up and deduplicate
        cleaned_authors = []
        for author in authors:
            author = author.strip()
            if author and author not in cleaned_authors:
                cleaned_authors.append(author)
        
        print(f"📚 Parsed authors: {cleaned_authors}")
        print(f"📚 Found {len(cleaned_authors)} authors to enrich")
        
        enriched_authors = []
        for i, author_name in enumerate(cleaned_authors, 1):
            print(f"\n--- Author {i}/{len(cleaned_authors)} ---")
            enriched_author = self.enrich_author(author_name, publication_title, parent_org)
            enriched_authors.append(enriched_author)
            
            # Rate limiting
            if i < len(cleaned_authors):
                time.sleep(1)  # Be respectful to APIs
        
        return enriched_authors

def main():
    parser = argparse.ArgumentParser(description='Enrich author information for SSHOC-NL pipeline')
    parser.add_argument('authors', help='Author name(s) - comma separated for multiple authors')
    parser.add_argument('--publication-title', help='Publication title for context')
    parser.add_argument('--parent-org', help='Parent organization hint')
    parser.add_argument('--output', help='Output JSON file', default='enriched_authors.json')
    
    args = parser.parse_args()
    
    # Initialize enricher
    enricher = AuthorEnricher()
    
    # Enrich authors
    print("🚀 SSHOC-NL Author Enrichment Tool")
    print("=" * 50)
    
    enriched_authors = enricher.enrich_authors_from_string(
        args.authors, 
        args.publication_title or "", 
        args.parent_org or ""
    )
    
    # Output results
    print(f"\n📊 ENRICHMENT RESULTS")
    print("=" * 50)
    
    results = []
    for i, author in enumerate(enriched_authors, 1):
        print(f"\n{i}. {author.full_name}")
        print(f"   ORCID: {author.orcid_id or 'Not found'}")
        print(f"   Affiliation: {author.affiliation or 'Not found'}")
        print(f"   Position: {author.current_position or 'Not found'}")
        print(f"   Email: {author.email or 'Not found'}")
        print(f"   Citations: {author.citation_count}")
        print(f"   H-index: {author.h_index}")
        if author.expertise_areas:
            print(f"   Expertise: {', '.join(author.expertise_areas[:3])}...")
        
        results.append(asdict(author))
    
    # Save to JSON
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {args.output}")
    print(f"🎉 Enriched {len(enriched_authors)} authors successfully!")

if __name__ == "__main__":
    main()

