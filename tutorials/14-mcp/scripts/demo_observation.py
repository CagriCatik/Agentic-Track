import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path.cwd() / "src"))

from local_dev_mcp.server import search_project_todos, add_note, list_notes, read_note

print("--- 🔍 Step 1: Scanning project for TODOs ---")
todos = search_project_todos("examples/sample_project")
for todo in todos:
    print(f"FOUND: {todo}")

print("\n--- 📝 Step 2: Saving a discovery note ---")
note_name = "discovery"
note_content = "The sample project has a TODO in app.py regarding input validation."
print(add_note(note_name, note_content))

print("\n--- 📂 Step 3: Listing current notes ---")
print(f"Notes in directory: {list_notes()}")

print("\n--- 📖 Step 4: Reading the note back ---")
print(f"Content of '{note_name}':\n{read_note(note_name)}")
