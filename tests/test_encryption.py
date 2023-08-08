# Issue with legacy openssl on x86 macOS

import pikepdf
import sys

test_fname = sys.argv[1]
doc = pikepdf.open(test_fname, password="encryption_test")

print("Successfully opened encrypted PDF")