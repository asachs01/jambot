# TNBGJ Songbook Import Scripts

This directory contains scripts for importing the Tennessee Bluegrass Jam songbook into the Jambot chord charts database.

## Files

- **`import_tnbgj_songbook.py`** - Main import script (requires database connection)
- **`validate_import_standalone.py`** - Validation script (no database required)
- **`inspect_transformation.py`** - Detailed transformation inspection for debugging

## Quick Start

### 1. Validate Without Database (Dry Run)

Run this first to verify the data transformation works correctly:

```bash
python3 scripts/validate_import_standalone.py
```

**Expected output:**
```
✓ All 8 songs validated successfully!
Ready for database import.
```

### 2. Run Import (Requires Database)

Set up database connection and run the import:

```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://user:password@host:port/database?sslmode=require"

# Run import
python3 scripts/import_tnbgj_songbook.py
```

**Expected output:**
```
IMPORT COMPLETE
Succeeded: 8
Failed:    0
Skipped:   0
Total:     8

✓ All songs imported successfully!
```

## Data Source

The import reads from:
```
/Users/asachs/Documents/projects/jambot/tnbgj_songbook_extracted.json
```

**Current status:** File contains 8 songs (not 51 as originally planned).

To change the source file, edit the `SOURCE_FILE` constant in the scripts.

## Schema Transformation

The import performs the following transformations:

### 1. Chord Progression Flattening

**Source:**
```json
{
  "section": "A Part",
  "columns": [
    {"label": "1", "measures": ["D", "D", "G", "D"]},
    {"label": "2", "measures": ["D", "D", "G", "G"]}
  ]
}
```

**Target:**
```json
{
  "label": "A Part",
  "rows": 8,
  "endings": null,
  "chords": ["D", "D", "G", "D", "D", "D", "G", "G"]
}
```

Chords are concatenated in **column-major order** (all measures from column 1, then all from column 2, etc.).

### 2. Lyrics Transformation

**Source:**
```json
[
  {"section": "verse", "lines": ["Line 1", "Line 2"]},
  {"section": "chorus", "lines": ["Chorus line"]}
]
```

**Target:**
```json
[
  {"label": "verse", "lines": ["Line 1", "Line 2"]},
  {"label": "chorus", "lines": ["Chorus line"]},
  {"_metadata": {"alternate_titles": [], "artist": null, "source": "imported", "status": "approved"}}
]
```

- Field rename: `section` → `label`
- Metadata embedded as final entry with `_metadata` key

### 3. Multi-Key Handling

Songs with multiple keys (e.g., Blue Ridge Cabin Home in G and A) are handled in two ways:

**Case 1: Explicit key fields in progressions**
```json
{
  "keys": ["G", "A"],
  "chord_progression": [
    {"section": "Verse", "key": "G", "columns": [...]},
    {"section": "Verse", "key": "A", "columns": [...]}
  ]
}
```
→ Creates 2 separate key entries, one for G and one for A, each with its own progression.

**Case 2: No explicit key fields**
```json
{
  "keys": ["G", "A"],
  "chord_progression": [
    {"section": "Verse", "columns": [...]}
  ]
}
```
→ Duplicates the progression for both G and A keys (same chords, different key context).

### 4. Database Field Mapping

| Source Field | Target Field | Notes |
|--------------|--------------|-------|
| `title` | `chord_charts.title` | Used for unique constraint |
| `title` | `chord_charts.chart_title` | Abbreviated if >20 chars |
| `lyrics` | `chord_charts.lyrics` | JSONB with transformed structure |
| `chord_progression` | `chord_charts.keys` | JSONB with flattened chords |
| `alternate_titles` | `lyrics._metadata.alternate_titles` | Embedded in lyrics JSONB |
| `artist` | `lyrics._metadata.artist` | Embedded in lyrics JSONB |
| `source` | `lyrics._metadata.source` | Always "imported" |
| `status` | `lyrics._metadata.status` | Always "approved" |
| *(fixed)* | `guild_id` | 0 (universal charts) |
| *(fixed)* | `created_by` | 0 (system import) |

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_import_songbook.py -v
```

**Test coverage:**
- Chord progression flattening (column-major order)
- Lyrics transformation (section → label rename)
- Metadata embedding in JSONB
- Multi-key song handling (explicit and inferred keys)
- Error handling for malformed data
- End-to-end import with database mocking
- Real data integration tests (Angeline the Baker, Blue Ridge Cabin Home)

**Current status:** 25/25 tests passing (100%)

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"

Use the standalone validation script instead:
```bash
python3 scripts/validate_import_standalone.py
```

### "OSError: [Errno 30] Read-only file system: '/app'"

The logger tries to create `/app` directory. Use standalone validation which has no dependencies:
```bash
python3 scripts/validate_import_standalone.py
```

### "DATABASE_URL environment variable is required"

For validation without database:
```bash
python3 scripts/validate_import_standalone.py
```

For actual import, set DATABASE_URL:
```bash
export DATABASE_URL="postgresql://..."
python3 scripts/import_tnbgj_songbook.py
```

## Import Idempotency

The import uses PostgreSQL's `ON CONFLICT DO UPDATE` to ensure idempotency:

- Running the import multiple times is safe
- Existing charts are updated with latest data
- `updated_at` timestamp is changed on updates
- No duplicate charts are created

## Verification

After import, verify the data:

```sql
-- Check total imported songs
SELECT COUNT(*) FROM chord_charts WHERE guild_id = 0;
-- Expected: 8

-- Check multi-key song (Blue Ridge Cabin Home)
SELECT title, jsonb_array_length(keys) as key_count
FROM chord_charts
WHERE title = 'Blue Ridge Cabin Home';
-- Expected: key_count = 2

-- Check metadata in lyrics
SELECT title, lyrics->'_metadata' as metadata
FROM chord_charts
WHERE title = 'Blue Moon of Kentucky';
-- Expected: metadata with artist='Bill Monroe', alternate_titles=['Blue Moon of Ky']

-- Check chord flattening
SELECT title, keys->>0 as first_key
FROM chord_charts
WHERE title = 'Angeline the Baker';
-- Expected: first_key contains sections with flat chords array
```

## Known Issues

1. **Song count discrepancy**: Original plan specified 51 songs, but extracted JSON contains only 8
   - Status: Import works correctly with available data
   - Action required: Verify extraction process or update acceptance criteria

2. **Alternate title search**: Metadata stored in JSONB but `search_chord_charts()` only queries `title` column
   - Status: Future enhancement needed for fuzzy search on alternate titles
   - Workaround: Use exact title search for now

## Next Steps

1. Run validation: `python3 scripts/validate_import_standalone.py`
2. Deploy to environment with DATABASE_URL configured
3. Run import: `python3 scripts/import_tnbgj_songbook.py`
4. Verify database state using SQL queries above
5. Test search functionality with imported charts
6. Consider adding remaining 43 songs to reach 51-song canon
