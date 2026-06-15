"""Tests for settings management."""

import pytest
from unittest.mock import patch

from qdrant_mcp.settings import Settings


class TestSettings:
    """Test settings configuration."""
    
    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            settings = Settings()
            assert settings.qdrant_url == "http://localhost:6333"
            assert settings.collection_name == "mcp_memory"
            assert settings.embedding_provider == "openai"
            assert settings.embedding_model == "text-embedding-3-small"
            assert settings.default_limit == 10
            assert settings.namespace == "qdrant"
    
    def test_environment_variables(self):
        """Test loading settings from environment."""
        env_vars = {
            "QDRANT_URL": "http://custom:6333",
            "COLLECTION_NAME": "custom_collection",
            "EMBEDDING_PROVIDER": "sentence-transformers",
            "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
            "DEFAULT_LIMIT": "20",
        }
        
        with patch.dict("os.environ", env_vars):
            settings = Settings()
            assert settings.qdrant_url == "http://custom:6333"
            assert settings.collection_name == "custom_collection"
            assert settings.embedding_provider == "sentence-transformers"
            assert settings.embedding_model == "all-MiniLM-L6-v2"
            assert settings.default_limit == 20
    
    def test_openai_api_key_validation(self):
        """Test OpenAI API key validation."""
        # Should raise error when using OpenAI without API key
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                Settings(embedding_provider="openai")
        
        # Should not raise error for sentence-transformers
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(embedding_provider="sentence-transformers")
            assert settings.openai_api_key is None
    
    def test_model_validation(self):
        """Test embedding model validation."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            # Valid OpenAI model
            settings = Settings(
                embedding_provider="openai",
                embedding_model="text-embedding-3-large"
            )
            assert settings.embedding_model == "text-embedding-3-large"
            
            # Invalid OpenAI model
            with pytest.raises(ValueError, match="Invalid OpenAI model"):
                Settings(
                    embedding_provider="openai",
                    embedding_model="invalid-model"
                )