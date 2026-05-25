with open('scarpy.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Let's locate the start line: "def _is_section_heading_text("
start_idx = -1
for i, line in enumerate(lines):
    if 'def _is_section_heading_text(' in line:
        start_idx = i
        break

# Let's locate the end line: "return _normalize_remedy_record(record)"
# and the blank lines following it.
end_idx = -1
for i, line in enumerate(lines):
    if i > start_idx and 'return _normalize_remedy_record(record)' in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found redundant parser block to remove: lines {start_idx+1} to {end_idx+1}")
    new_lines = lines[:start_idx] + lines[end_idx+1:]
    with open('scarpy.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Deduplicated scarpy.py successfully!")
else:
    print("Error: Could not locate redundant parser block!")
