import json
import sys
import uuid

path, after_cell_id, cell_type, source_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(source_path) as f:
    new_source = f.read()

with open(path) as f:
    nb = json.load(f)

new_cell = {
    "cell_type": cell_type,
    "id": uuid.uuid4().hex[:8],
    "metadata": {},
    "source": new_source.splitlines(keepends=True),
}
if cell_type == "code":
    new_cell["outputs"] = []
    new_cell["execution_count"] = None

idx = None
for i, cell in enumerate(nb["cells"]):
    if cell.get("id") == after_cell_id:
        idx = i
        break

if idx is None:
    print(f"ERROR: cell id {after_cell_id} not found")
    sys.exit(1)

nb["cells"].insert(idx + 1, new_cell)

with open(path, "w") as f:
    json.dump(nb, f, indent=1)
    f.write("\n")

print(f"OK: inserted new {cell_type} cell {new_cell['id']} after {after_cell_id}")
