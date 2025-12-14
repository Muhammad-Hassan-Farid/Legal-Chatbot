#!/usr/bin/env python3
"""
Test improved extraction logic for QanoonMate responses
"""

# Sample output from the test above
sample_text = """New Chat
Global Search
MODE
Chat
Interactive legal conversations
Summarizer
Summarize legal documents
Drafting
Draft legal documents
Settings
1
Dec 14
100%
16px
card
Sign In
Chat Mode
What are fundamental rights in Pakistan?
In Pakistan, fundamental rights are enshrined in the Constitution of the Islamic Republic of Pakistan, 1973. Here are
 the key articles that outline these rights:
Article 4:
Guarantees the right to protection of law and fair treatment. It states that no person shall be deprived of life, lib
erty, or property except in accordance with the law.
Article 15:
Ensures the right to move freely throughout Pakistan and to reside in any part of the country, subject to reasonable 
restrictions in the public interest.
Article 19:
Provides the right to freedom of speech and expression, including freedom of the press, with certain reasonable restr
ictions for public order and morality.
Article 23:
Grants the right to acquire, hold, and dispose of property anywhere in Pakistan, subject to constitutional and legal 
restrictions.
Article 16:
Affirms the right to assemble peacefully and without arms, subject to reasonable restrictions for public order.
Article 17:
Allows citizens to form associations or unions, including political parties, with reasonable restrictions for the int
egrity of
AI is typing...
⚠️
QanoonMate can make mistakes. Please verify important information."""

def test_extraction():
    """Test the improved extraction logic"""
    query = "What are fundamental rights in Pakistan?"
    
    print("Original text length:", len(sample_text))
    print("\nOriginal text preview:")
    print(sample_text[:200])
    print("\n...\n")
    print(sample_text[-200:])
    
    print("\n" + "="*70)
    print("TESTING IMPROVED EXTRACTION")
    print("="*70)
    
    lines = sample_text.split('\n')
    print(f"\nTotal lines: {len(lines)}")
    
    # Keywords to skip (UI elements)
    skip_keywords = {
        "MODE", "Chat", "Interactive legal conversations",
        "Summarizer", "Summarize legal documents",
        "Drafting", "Draft legal documents",
        "Settings", "Sign In", "Chat Mode", "Hello, User",
        "Try asking:", "Global Search", "100%", "16px", "card",
        "New Chat", "Business Registration", "Tenant Rights",
        "Intellectual Property", "Employment Law",
        "What are the legal requirements", "Explain the tenant",
        "How can I protect", "What are the key labor", "Dec 14",
        "AI is typing", "QanoonMate can make mistakes",
        "Please verify important information"
    }
    
    # Stopping phrases (lines containing these mark end of response)
    stopping_phrases = [
        "AI is typing",
        "can make mistakes",
        "verify important information",
        "QanoonMate"
    ]
    
    # Strategy: Extract from first substantial line after query to last substantial line
    content_lines = []
    found_query = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            continue
        
        # Skip very short lines (UI)
        if len(stripped) < 10:
            continue
        
        # Check for stopping phrases
        if any(phrase in stripped for phrase in stopping_phrases):
            print(f"\nLine {i}: STOPPING - '{stripped[:50]}'")
            break
        
        # Skip known UI keywords
        if stripped in skip_keywords or any(kw in stripped for kw in skip_keywords):
            print(f"Line {i}: SKIP (UI) - '{stripped[:50]}'")
            continue
        
        # Skip the query itself
        if stripped.lower() == query.lower():
            print(f"Line {i}: SKIP (QUERY) - '{stripped[:50]}'")
            found_query = True
            continue
        
        # This looks like content
        if found_query or (len(stripped) > 20 and "Article" in stripped):
            # Found response content
            print(f"Line {i}: KEEP - '{stripped[:60]}'")
            content_lines.append(stripped)
    
    # Join lines
    response = '\n'.join(content_lines)
    
    print("\n" + "="*70)
    print("EXTRACTED RESPONSE")
    print("="*70)
    print(f"\nExtracted {len(response)} characters from {len(content_lines)} lines")
    print(f"\nContent preview:")
    print(response[:500])
    print("\n...\n")
    print(response[-500:])
    
    # Validate
    print("\n" + "="*70)
    print("VALIDATION")
    print("="*70)
    
    if "Drafting" in response:
        print("✗ ERROR: 'Drafting' still in response")
    else:
        print("✓ OK: No 'Drafting' text")
    
    if "AI is typing" in response:
        print("✗ ERROR: 'AI is typing' still in response")
    else:
        print("✓ OK: No 'AI is typing' text")
    
    if len(response) > 300:
        print(f"✓ OK: Sufficient content ({len(response)} chars)")
    else:
        print(f"✗ ERROR: Insufficient content ({len(response)} chars)")
    
    if "Article 4" in response and "Article 15" in response:
        print("✓ OK: Contains expected content (Articles)")
    else:
        print("✗ ERROR: Missing expected content")

if __name__ == "__main__":
    test_extraction()
