# Issue with legacy openssl on x86 macOS

import pikepdf
from pathlib import Path

test_fname = Path(__file__).parent / "encryption_test.pdf"
doc = pikepdf.open(test_fname, password="encryption_test")

print("Successfully opened encrypted PDF")