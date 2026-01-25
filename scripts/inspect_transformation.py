#!/usr/bin/env python3
"""Inspect a transformed song to verify schema mapping."""

import json
import sys

sys.path.insert(0, 'scripts')
from validate_import_standalone import transform_song, SOURCE_FILE

with open(SOURCE_FILE) as f:
    data = json.load(f)

# Transform Blue Ridge Cabin Home (multi-key example)
song = [s for s in data['songbook']['songs'] if s['title'] == 'Blue Ridge Cabin Home'][0]
transformed = transform_song(song)

print("=" * 60)
print("TRANSFORMATION INSPECTION: Blue Ridge Cabin Home")
print("=" * 60)
print("\nOriginal song keys:", song['keys'])
print("Transformed keys count:", len(transformed['keys']))
print("\nTransformed structure:")
print(json.dumps(transformed, indent=2))
