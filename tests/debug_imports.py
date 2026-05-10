print("1. Importing tensorflow...")
import tensorflow as tf
print("2. Importing numpy...")
import numpy as np
print("3. Importing PIL...")
import PIL
print("4. Importing pypdf...")
import pypdf
print("5. Importing pdfminer...")
import pdfminer
print("6. Importing neo4j...")
try:
    import neo4j
    print("   Neo4j imported.")
except ImportError:
    print("   Neo4j missing (expected).")

print("7. Importing api.main...")
try:
    from api.main import app
    print("   api.main imported.")
except Exception as e:
    print(f"!!! CRASH IN API.MAIN: {e}")
    import traceback
    traceback.print_exc()

print("8. DONE.")
