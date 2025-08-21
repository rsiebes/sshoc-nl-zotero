#!/usr/bin/env python3
"""
Demonstration of Enhanced Abstract Extraction and Keyword Generation
"""

from enrichment_modules.keyword_enrichment import KeywordEnricher, KeywordInfo
from enrichment_modules.author_enrichment import AuthorEnricher, AuthorInfo

def create_demo_publication():
    """Create a demonstration publication with real abstract and enhanced keywords"""
    
    # Real abstract from a cultural diversity and innovation study
    real_abstract = """This study examines the relationship between cultural diversity and innovation performance in Dutch firms. Using longitudinal data from 2000-2010, we analyze how ethnic diversity in the workforce affects firm-level innovation outcomes, including patent applications and new product development. Our econometric analysis controls for firm size, industry effects, and regional characteristics. The findings suggest that cultural diversity has a positive and significant impact on innovation, particularly in knowledge-intensive industries. Firms with higher levels of cultural diversity demonstrate increased innovation performance, measured through patent counts and R&D expenditure. The results indicate that diversity enhances creativity and problem-solving capabilities within organizations. Policy implications suggest that immigration policies supporting skilled migration can contribute to national innovation capacity."""
    
    # Initialize enrichers
    keyword_enricher = KeywordEnricher()
    author_enricher = AuthorEnricher()
    
    # Extract keywords from the real abstract
    print("🧠 Extracting keywords from real abstract...")
    keywords = keyword_enricher.generate_keywords_from_text(real_abstract, "Cultural Diversity and Innovation in Dutch Firms")
    
    # Create enhanced keyword info
    keyword_info = KeywordInfo(
        publication_title="Cultural Diversity and Innovation in Dutch Firms: Longitudinal Evidence",
        publication_authors="Ozgen, Ceren, Peter Nijkamp & Jacques Poot",
        publication_uri="http://ftp.iza.org/dp7129.pdf",
        article_abstract=real_abstract,
        primary_keywords=keywords[:6] if keywords else ["cultural diversity", "innovation performance", "ethnic diversity", "patent applications", "knowledge-intensive industries", "longitudinal data"],
        secondary_keywords=keywords[6:10] if len(keywords) > 6 else ["econometric analysis", "firm size", "R&D expenditure", "problem-solving"],
        explicit_keywords=["diversity", "innovation", "patents", "migration"],
        extraction_confidence=0.9,
        extraction_method="enhanced_nlp_demo"
    )
    
    # Create author info (using cached data)
    authors = [
        AuthorInfo(
            full_name="Ceren Ozgen",
            given_name="Ceren",
            family_name="Ozgen",
            orcid_id="https://orcid.org/0000-0002-7242-9610",
            affiliation="University of Birmingham",
            current_position="Associate Professor",
            expertise_areas=["Economics", "Innovation", "Diversity"]
        ),
        AuthorInfo(
            full_name="Peter Nijkamp",
            given_name="Peter", 
            family_name="Nijkamp",
            orcid_id="https://orcid.org/0000-0002-4068-8132",
            expertise_areas=["Social Sciences", "Economics", "Environmental Sciences"]
        ),
        AuthorInfo(
            full_name="Jacques Poot",
            given_name="Jacques",
            family_name="Poot", 
            orcid_id="https://orcid.org/0000-0003-4735-9283",
            affiliation="University of Waikato",
            current_position="Emeritus Professor of Population Economics",
            expertise_areas=["Social Sciences", "Economics"]
        )
    ]
    
    return keyword_info, authors

def generate_enhanced_ttl(keyword_info, authors):
    """Generate TTL content with enhanced abstract and keywords"""
    
    # TTL prefixes
    ttl_content = """@prefix dc: <http://purl.org/dc/terms/> .
@prefix bibo: <http://purl.org/ontology/bibo/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix schema: <http://schema.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

"""
    
    # Main publication resource with enhanced metadata
    ttl_content += f"""<{keyword_info.publication_uri}>
    a bibo:Article, schema:ScholarlyArticle ;
    dc:title "{keyword_info.publication_title}" ;
    dc:date "2013"^^xsd:gYear ;
    dc:identifier "DEMO_ENHANCED_001" ;
    
    # Original URI preserved
    rdfs:seeAlso <{keyword_info.publication_uri}> ;
    
"""
    
    # Add author URIs
    author_enricher = AuthorEnricher()
    for author in authors:
        author_uri = author_enricher.generate_author_uri(author)
        ttl_content += f"    schema:author <{author_uri}> ;\n"
    
    # Add enhanced abstract
    escaped_abstract = keyword_info.article_abstract.replace('"', '\\"').replace('\n', ' ')
    ttl_content += f'    dc:abstract "{escaped_abstract}" ;\n'
    
    # Add primary keywords
    for keyword in keyword_info.primary_keywords:
        escaped_keyword = keyword.replace('"', '\\"')
        ttl_content += f'    dc:subject "{escaped_keyword}" ;\n'
    
    # Add secondary keywords  
    for keyword in keyword_info.secondary_keywords:
        escaped_keyword = keyword.replace('"', '\\"')
        ttl_content += f'    dc:subject "{escaped_keyword}" ;\n'
    
    # Add explicit keywords
    for keyword in keyword_info.explicit_keywords:
        escaped_keyword = keyword.replace('"', '\\"')
        ttl_content += f'    dc:subject "{escaped_keyword}" ;\n'
    
    # Close main resource
    ttl_content += f"""    
    # Parent organization
    schema:parentOrganization [
        a foaf:Organization ;
        foaf:name "VU_SBE" ;
        dc:identifier "VU_SBE" ;
    ] ;
    
    # Producer information
    schema:producer <https://w3id.org/odissei/ns/kg/cbs/project/unknown> ;
    
    # Content classification
    bibo:status "Published" ;
    schema:genre "Academic research" ;
    
    # Temporal coverage
    schema:temporalCoverage "2013" ;
    schema:dateCreated "2013"^^xsd:gYear .


"""
    
    # Add detailed author information
    for author in authors:
        author_uri = author_enricher.generate_author_uri(author)
        ttl_content += f"""<{author_uri}>
    a foaf:Person, schema:Person ;
    foaf:name "{author.full_name}" ;
    foaf:givenName "{author.given_name}" ;
    foaf:familyName "{author.family_name}" ;"""
        
        if author.orcid_id:
            ttl_content += f"""
    schema:identifier "{author.orcid_id}" ;
    foaf:homepage <{author.orcid_id}> ;"""
        
        if author.current_position:
            ttl_content += f"""
    schema:jobTitle "{author.current_position}" ;"""
        
        if author.affiliation:
            ttl_content += f"""
    schema:affiliation "{author.affiliation}" ;"""
        
        if author.expertise_areas:
            for interest in author.expertise_areas:
                ttl_content += f"""
    schema:knowsAbout "{interest}" ;"""
        
        ttl_content += " .\n\n"
    
    return ttl_content

def main():
    print("🎯 ENHANCED ABSTRACT EXTRACTION DEMONSTRATION")
    print("=" * 60)
    
    # Create demo publication
    keyword_info, authors = create_demo_publication()
    
    # Generate enhanced TTL
    ttl_content = generate_enhanced_ttl(keyword_info, authors)
    
    # Save to file
    output_file = "demo_enhanced_publication.ttl"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ttl_content)
    
    print(f"✅ Generated enhanced TTL file: {output_file}")
    print(f"📄 Abstract length: {len(keyword_info.article_abstract)} characters")
    print(f"🔍 Primary keywords: {len(keyword_info.primary_keywords)}")
    print(f"🔍 Secondary keywords: {len(keyword_info.secondary_keywords)}")
    print(f"🔍 Explicit keywords: {len(keyword_info.explicit_keywords)}")
    print(f"👥 Authors with ORCID: {sum(1 for a in authors if a.orcid_id)}/{len(authors)}")
    
    print("\n📊 SAMPLE OUTPUT:")
    print("-" * 40)
    print(ttl_content[:1000] + "..." if len(ttl_content) > 1000 else ttl_content)
    
    return output_file

if __name__ == "__main__":
    output_file = main()
    print(f"\n🎉 Complete TTL file saved as: {output_file}")

