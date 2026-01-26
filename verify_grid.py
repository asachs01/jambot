from src.chart_generator import parse_chord_input
import math

# Test with exactly 32 chords (4 columns × 8 rows)
chords = ' '.join(['A'] * 32)
data = parse_chord_input(
    title='Grid Test',
    key='A',
    section_labels='Test',
    chords_text=chords
)

section = data['keys'][0]['sections'][0]
rows = section['rows']
chords_count = len(section['chords'])
cols = max(1, math.ceil(chords_count / rows))

print(f"Chords: {chords_count}")
print(f"Rows: {rows}")
print(f"Columns: {cols}")
print(f"Expected grid: 4 columns × 8 rows = 32 cells")
print(f"Actual grid: {cols} columns × {rows} rows = {cols * rows} cells")
print(f"Match: {cols == 4 and rows == 8}")
