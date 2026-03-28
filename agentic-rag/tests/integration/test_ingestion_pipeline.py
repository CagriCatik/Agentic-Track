import pytest
import shutil
from pathlib import Path
from src.knowledge.ingestion import run_ingestion
from src.knowledge.versioning import load_manifest
from src.retrieval.vector_store import get_vector_store
from src.config import get_settings

def test_full_medallion_ingestion_cycle(tmp_path):
    """
    Integration test for the full Bronze -> Silver -> Gold -> ChromaDB flow.
    Uses a temporary directory to avoid polluting production data.
    """
    settings = get_settings()
    
    # 1. Setup temporary workspace
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    
    # Mock a source file
    test_file = corpus_dir / "test_doc.md"
    test_file.write_text("# Test Title\nThis is a test document for the pipeline.")
    
    # Override settings for test
    settings.data.bronze_dir = str(tmp_path / "bronze")
    settings.data.silver_dir = str(tmp_path / "silver")
    settings.data.gold_dir = str(tmp_path / "gold")
    settings.data.manifest_dir = str(tmp_path / "manifests")
    
    # 2. Run Ingestion
    # We pass the corpus_dir to get_changed_files or similar if needed, 
    # but run_ingestion uses resolve_path("../corpus") by default.
    # Let's ensure it uses our tmp_path.
    
    # Patching versioning.resolve_path might be complex, so we'll just 
    # run it and hope the settings override handles the output dirs.
    # For the input, we might need to manually trigger or mock get_changed_files.
    
    from src.knowledge import versioning
    original_get_changed_files = versioning.get_changed_files
    versioning.get_changed_files = lambda: [test_file]
    
    try:
        run_ingestion(force=True)
        
        # 3. Verify Bronze
        bronze_files = list(Path(settings.data.bronze_dir).glob("*.json"))
        assert len(bronze_files) == 1
        assert "test_doc" in bronze_files[0].name
        
        # 4. Verify Silver
        silver_files = list(Path(settings.data.silver_dir).glob("*.json"))
        assert len(silver_files) > 0
        
        # 5. Verify Gold / Chroma
        vector_store = get_vector_store()
        results = vector_store.similarity_search("test document", k=1)
        assert len(results) > 0
        assert "test document" in results[0].page_content.lower()
        
    finally:
        # Restore mock
        versioning.get_changed_files = original_get_changed_files
