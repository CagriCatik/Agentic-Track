import sys
from pathlib import Path

# Add src to path if not already there
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from local_dev_mcp.server import add_note, list_notes, read_note, append_note, NOTES_DIR

def test_note_lifecycle():
    # Cleanup before test
    test_note_name = "test-note-123"
    test_note_path = NOTES_DIR / f"{test_note_name}.md"
    if test_note_path.exists():
        test_note_path.unlink()

    # Test add_note
    content = "Hello MCP"
    result = add_note(test_note_name, content)
    assert "Saved note" in result
    assert test_note_path.exists()
    assert test_note_path.read_text(encoding="utf-8") == content

    # Test list_notes
    notes = list_notes()
    assert f"{test_note_name}.md" in notes

    # Test read_note
    read_content = read_note(test_note_name)
    assert read_content == content

    # Test append_note
    append_content = " More content"
    result = append_note(test_note_name, append_content)
    assert "Updated note" in result
    assert test_note_path.read_text(encoding="utf-8") == content + "\n" + append_content

    # Cleanup after test
    test_note_path.unlink()

def test_invalid_note_name():
    try:
        add_note("", "content")
    except ValueError as e:
        assert "Invalid note name" in str(e)
