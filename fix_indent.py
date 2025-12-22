
import sys

file_path = r"C:\Users\Adrian\Documents\Repos\Tetra\tetra_gui_modern.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Range to fix: 1185 to 1252 (1-based) -> 1184 to 1252 (0-based)
# Actually, let's look at the lines around 1180 to be sure.

start_line_idx = 1184 # Line 1185
end_line_idx = 1253   # Line 1254 (exclusive)

# We want to indent lines 1185-1247 by 4 spaces.
# And indent lines 1248-1252 by 4 spaces.
# Wait, 1248 was at 20 spaces, needs to be 24.
# 1185 was at 24 spaces, needs to be 28.
# So basically indent everything from 1185 to 1252 by 4 spaces.

# Let's verify line 1185 content
if "if self.monitor_raw:" not in lines[1184]:
    print(f"Error: Line 1185 is not what expected: {lines[1184]}")
    sys.exit(1)

# Let's verify line 1248 content (index 1247)
if "except Exception as decode_err:" not in lines[1247]:
    print(f"Error: Line 1248 is not what expected: {lines[1247]}")
    sys.exit(1)

# Apply indentation
for i in range(1184, 1253):
    if lines[i].strip(): # Don't indent empty lines if they are just newlines
        lines[i] = "    " + lines[i]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Successfully fixed indentation.")
