# -*- coding: utf-8 -*-
"""
Test script to verify UTF-8 encoding is working properly
"""
import sys
import io
import locale

# Force UTF-8 on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("\n" + "="*60)
print("UTF-8 ENCODING TEST")
print("="*60)

# Check encoding settings
print(f"\nPython Version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"Stdout encoding: {sys.stdout.encoding}")
print(f"Stderr encoding: {sys.stderr.encoding}")
print(f"Default encoding: {sys.getdefaultencoding()}")
print(f"Filesystem encoding: {sys.getfilesystemencoding()}")
print(f"Locale preferred encoding: {locale.getpreferredencoding()}")

# Test Hindi text
print("\n" + "-"*60)
print("HINDI TEXT TEST:")
print("-"*60)

hindi_texts = [
    "नमस्ते - Hello",
    "क्या तुम हिंदी बोल सकते हो? - Can you speak Hindi?",
    "यह एक परीक्षण है - This is a test",
    "कंप्यूटर - Computer",
    "प्रोग्रामिंग - Programming"
]

for text in hindi_texts:
    print(f"✓ {text}")

print("\n" + "="*60)
print("If you see Hindi text above, UTF-8 is working correctly!")
print("="*60 + "\n")
