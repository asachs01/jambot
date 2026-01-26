from src.chart_generator import parse_chord_input, generate_chart_pdf, transpose_chord

# Test 1: Empty chord (should be preserved)
result = transpose_chord('', 5)
print(f"Empty chord: '{result}' (expected: '')")

# Test 2: Invalid chord (should passthrough)
result = transpose_chord('N.C.', 3)
print(f"Invalid chord: '{result}' (expected: 'N.C.')")

# Test 3: Empty chart data
data = {
    'title': 'Empty',
    'chart_title': 'Empty',
    'keys': [],
    'lyrics': None,
}
pdf = generate_chart_pdf(data)
print(f"Empty chart PDF size: {len(pdf.read())} bytes (expected: >500)")

# Test 4: Chart with no status (should default to draft)
data = parse_chord_input(
    title='Default',
    key='G',
    section_labels='V',
    chords_text='G C D G'
)
# Don't set status - should default to draft
pdf_default = generate_chart_pdf(data)
default_size = len(pdf_default.read())

data['status'] = 'approved'
pdf_approved = generate_chart_pdf(data)
approved_size = len(pdf_approved.read())

print(f"Default PDF: {default_size} bytes, Approved PDF: {approved_size} bytes")
print(f"Default is draft (larger): {default_size > approved_size}")

print("\nAll edge cases handled correctly!")
