from src.chart_generator import parse_chord_input, generate_chart_pdf

# Create test chart
data = parse_chord_input(
    title='Old Joe Clark',
    key='A',
    section_labels='A Part,B Part',
    chords_text='A A A A | A A D D\n\nA A D D | E E A A',
    lyrics_text='Round and round, Old Joe Clark\nRound and round I say\n\nHe\'d follow me ten thousand miles\nTo hear my fiddle play'
)

# Generate draft PDF
data['status'] = 'draft'
pdf = generate_chart_pdf(data)
with open('/tmp/test_draft.pdf', 'wb') as f:
    f.write(pdf.read())

# Generate approved PDF
data['status'] = 'approved'
pdf = generate_chart_pdf(data)
with open('/tmp/test_approved.pdf', 'wb') as f:
    f.write(pdf.read())

print("PDFs generated:")
print("  Draft: /tmp/test_draft.pdf")
print("  Approved: /tmp/test_approved.pdf")
