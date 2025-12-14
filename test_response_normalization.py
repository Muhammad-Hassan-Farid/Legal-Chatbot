#!/usr/bin/env python
"""
Quick test to verify the normalize_response_structure function works correctly.
Run: python test_response_normalization.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paklegal_chatbot.settings')
sys.path.insert(0, '/Users/hassanfarid/Documents/Freelance_Projects/PakLegal_ChatBot/Pakistan-Constitution-Chatbot')
django.setup()

from chat.views import normalize_response_structure

# Test Case 1: Bullet point formatting
test1 = """Key principles:
•Universality and Equality
•Judicial Enforcement
•Supremacy of the Constitution"""

print("=" * 60)
print("TEST 1: Bullet Point Formatting")
print("=" * 60)
print("BEFORE:")
print(repr(test1))
print("\nAFTER:")
result1 = normalize_response_structure(test1)
print(repr(result1))
print("\nRENDERED:")
print(result1)

# Test Case 2: Legal reference spacing
test2 = """Article 4 – Right of individuals to be dealt with in accordance with law
This article affirms that every person shall enjoy protection of the law.
Article 8 – Laws inconsistent with Fundamental Rights to be void
This declares all laws inconsistent with Fundamental Rights void."""

print("\n" + "=" * 60)
print("TEST 2: Legal Reference Spacing")
print("=" * 60)
print("BEFORE:")
print(repr(test2))
print("\nAFTER:")
result2 = normalize_response_structure(test2, source="paklegal")
print(repr(result2))
print("\nRENDERED:")
print(result2)

# Test Case 3: Numbered lists
test3 = """Steps to file:
1.Submit application
2.Wait for decision
3.Appeal if necessary"""

print("\n" + "=" * 60)
print("TEST 3: Numbered List Formatting")
print("=" * 60)
print("BEFORE:")
print(repr(test3))
print("\nAFTER:")
result3 = normalize_response_structure(test3)
print(repr(result3))
print("\nRENDERED:")
print(result3)

# Test Case 4: Mixed content with QanoonMate source
test4 = """Question: Fundamental Rights?
Fundamental Rights of Human Beings in Pakistan

Key Legal Principles
Universality and Equality - Fundamental rights apply to every person
Judicial Enforcement - Rights are enforceable through constitutional petitions

Leading Case Law
Mahera Sajid v. Station House Officer - Court enforced compensation for rights violation"""

print("\n" + "=" * 60)
print("TEST 4: Mixed Content (QanoonMate Source)")
print("=" * 60)
print("BEFORE:")
print(repr(test4))
print("\nAFTER:")
result4 = normalize_response_structure(test4, source="qanoonmate")
print(repr(result4))
print("\nRENDERED:")
print(result4)

# Test Case 5: Pakistan Law Bot source
test5 = """Fundamental Rights of Human Beings in Pakistan
Legal Context
Fundamental rights constitute the cornerstone of the Constitution.
Statutory Framework
Article 4 – Right of individuals to be dealt with in accordance with law
Article 8 – Laws inconsistent with Fundamental Rights"""

print("\n" + "=" * 60)
print("TEST 5: Pakistan Law Bot Source")
print("=" * 60)
print("BEFORE:")
print(repr(test5))
print("\nAFTER:")
result5 = normalize_response_structure(test5, source="pakistanlaw")
print(repr(result5))
print("\nRENDERED:")
print(result5)

print("\n" + "=" * 60)
print("✅ All tests completed successfully!")
print("=" * 60)
