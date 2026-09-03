import json
import sys

path, cell_id, source_path = sys.argv[1], sys.argv[2], sys.argv[3]
with open(source_path) as f:
    new_source = f.read()

with open(path) as f:
    nb = json.load(f)

found = False
for cell in nb["cells"]:
    if cell.get("id") == cell_id:
        cell["source"] = new_source.splitlines(keepends=True)
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        found = True
        break

if not found:
    print(f"ERROR: cell id {cell_id} not found")
    sys.exit(1)

with open(path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")

print(f"OK: updated cell {cell_id}")
