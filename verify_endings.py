from src.chart_generator import parse_chord_input, generate_chart_pdf

# Create chart with ending markers
data = parse_chord_input(
    title='Ending Test',
    key='G',
    section_labels='A Part',
    chords_text='G C D G | G C D G'
)

# Add ending markers manually (column 0 = ending 1, column 1 = ending 2)
data['keys'][0]['sections'][0]['endings'] = [
    {'column': 0, 'ending': 1},
    {'column': 1, 'ending': 2}
]

pdf = generate_chart_pdf(data)
with open('/tmp/test_endings.pdf', 'wb') as f:
    f.write(pdf.read())

print("PDF with endings generated: /tmp/test_endings.pdf")
print(f"Endings data: {data['keys'][0]['sections'][0]['endings']}")
