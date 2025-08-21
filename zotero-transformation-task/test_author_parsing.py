#!/usr/bin/env python3
"""
Test script to understand author parsing for the 26th publication
"""

def parse_authors_manual(authors_string):
    """Manual parsing to understand the structure"""
    print(f"Original string: '{authors_string}'")
    
    # The format appears to be: "Dijkstra, Aletta, Eva U.B. Kibele, Antonia Verweij, Fons van der Lucht & Fanny Janssen"
    # This suggests:
    # 1. Aletta Dijkstra (Last, First format for first author)
    # 2. Eva U.B. Kibele 
    # 3. Antonia Verweij
    # 4. Fons van der Lucht
    # 5. Fanny Janssen (after &)
    
    authors = []
    
    # Split by ' & ' first
    if ' & ' in authors_string:
        parts = authors_string.split(' & ')
        main_part = parts[0].strip()
        last_author = parts[1].strip()
        authors.append(last_author)
        print(f"Last author (after &): '{last_author}'")
    else:
        main_part = authors_string.strip()
    
    # Now parse the main part
    print(f"Main part to parse: '{main_part}'")
    
    # Split by comma
    comma_parts = [p.strip() for p in main_part.split(',')]
    print(f"Comma parts: {comma_parts}")
    
    if len(comma_parts) >= 2:
        # First author: "Dijkstra" (last), "Aletta" (first)
        first_author = f"{comma_parts[1]} {comma_parts[0]}"
        authors.insert(0, first_author)
        print(f"First author: '{first_author}'")
        
        # The rest should be individual authors
        # "Eva U.B. Kibele", "Antonia Verweij", "Fons van der Lucht"
        for i in range(2, len(comma_parts)):
            if comma_parts[i].strip():
                authors.insert(-1, comma_parts[i].strip())
                print(f"Author {i-1}: '{comma_parts[i].strip()}'")
    
    print(f"\nFinal parsed authors: {authors}")
    return authors

# Test with the 26th publication
test_string = "Dijkstra, Aletta, Eva U.B. Kibele, Antonia Verweij, Fons van der Lucht & Fanny Janssen"
parse_authors_manual(test_string)

