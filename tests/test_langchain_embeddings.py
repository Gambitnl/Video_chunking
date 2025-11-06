"""
Tests for src/langchain/embeddings.py - Embedding Service
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.langchain.embeddings import EmbeddingService


@pytest.fixture
def mock_sentence_transformer(monkeypatch):
    """Mock SentenceTransformer to avoid loading actual models."""
    mock_model = MagicMock()
    mock_model.encode.return_value = Mock()  # Will be configured per test
    mock_model.get_sentence_embedding_dimension.return_value = 384

    mock_st_class = MagicMock(return_value=mock_model)

    # Mock the sentence_transformers module
    mock_st_module = MagicMock()
    mock_st_module.SentenceTransformer = mock_st_class

    monkeypatch.setitem(__import__('sys').modules, 'sentence_transformers', mock_st_module)

    return {
        'model': mock_model,
        'class': mock_st_class,
        'module': mock_st_module
    }


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_init_with_default_model(self, mock_sentence_transformer):
        """Test initialization with default model name."""
        service = EmbeddingService()

        # Verify default model is used
        mock_sentence_transformer['class'].assert_called_once_with("all-MiniLM-L6-v2")
        assert service.model_name == "all-MiniLM-L6-v2"
        assert service.model == mock_sentence_transformer['model']

    def test_init_with_custom_model(self, mock_sentence_transformer):
        """Test initialization with custom model name."""
        service = EmbeddingService(model_name="all-mpnet-base-v2")

        # Verify custom model is used
        mock_sentence_transformer['class'].assert_called_once_with("all-mpnet-base-v2")
        assert service.model_name == "all-mpnet-base-v2"

    def test_init_raises_error_if_sentence_transformers_not_installed(self, monkeypatch):
        """Test that RuntimeError is raised if sentence-transformers is not installed."""
        # Remove sentence_transformers from sys.modules
        import sys
        if 'sentence_transformers' in sys.modules:
            monkeypatch.delitem(sys.modules, 'sentence_transformers')

        # Mock import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == 'sentence_transformers':
                raise ImportError("No module named 'sentence_transformers'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr('builtins.__import__', mock_import)

        with pytest.raises(RuntimeError, match="sentence-transformers not installed"):
            EmbeddingService()


class TestEmbed:
    """Tests for embed method (single text)."""

    def test_embed_happy_path(self, mock_sentence_transformer):
        """Test embedding a single text successfully."""
        service = EmbeddingService()

        # Configure mock to return numpy array (which has .tolist())
        import numpy as np
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_sentence_transformer['model'].encode.return_value = mock_embedding

        result = service.embed("Hello world")

        # Verify encode was called correctly
        mock_sentence_transformer['model'].encode.assert_called_once_with(
            "Hello world",
            convert_to_numpy=True
        )

        # Verify result is a list of floats
        assert result == [0.1, 0.2, 0.3]
        assert isinstance(result, list)

    def test_embed_raises_on_error(self, mock_sentence_transformer):
        """Test that exceptions during embedding are propagated."""
        service = EmbeddingService()

        mock_sentence_transformer['model'].encode.side_effect = Exception("Encoding failed")

        with pytest.raises(Exception, match="Encoding failed"):
            service.embed("test")


class TestEmbedBatch:
    """Tests for embed_batch method (multiple texts)."""

    def test_embed_batch_happy_path(self, mock_sentence_transformer):
        """Test embedding multiple texts successfully."""
        service = EmbeddingService()

        # Configure mock to return numpy array
        import numpy as np
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6]
        ])
        mock_sentence_transformer['model'].encode.return_value = mock_embeddings

        texts = ["Hello world", "How are you?"]
        result = service.embed_batch(texts, batch_size=32)

        # Verify encode was called correctly
        mock_sentence_transformer['model'].encode.assert_called_once()
        call_args = mock_sentence_transformer['model'].encode.call_args[1]

        assert call_args['batch_size'] == 32
        assert call_args['show_progress_bar'] is False  # len(texts) = 2, not > 100
        assert call_args['convert_to_numpy'] is True

        # Verify result is list of lists
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        assert isinstance(result, list)
        assert isinstance(result[0], list)

    def test_embed_batch_shows_progress_for_large_batches(self, mock_sentence_transformer):
        """Test that progress bar is shown for large batches (>100 texts)."""
        service = EmbeddingService()

        import numpy as np
        mock_embeddings = np.array([[0.1, 0.2, 0.3] for _ in range(150)])
        mock_sentence_transformer['model'].encode.return_value = mock_embeddings

        texts = [f"Text {i}" for i in range(150)]
        service.embed_batch(texts, batch_size=64)

        # Verify show_progress_bar was True
        call_args = mock_sentence_transformer['model'].encode.call_args[1]
        assert call_args['show_progress_bar'] is True  # len(texts) = 150 > 100

    def test_embed_batch_with_custom_batch_size(self, mock_sentence_transformer):
        """Test embedding with custom batch size."""
        service = EmbeddingService()

        import numpy as np
        mock_embeddings = np.array([[0.1, 0.2]])
        mock_sentence_transformer['model'].encode.return_value = mock_embeddings

        service.embed_batch(["test"], batch_size=16)

        # Verify custom batch size was used
        call_args = mock_sentence_transformer['model'].encode.call_args[1]
        assert call_args['batch_size'] == 16

    def test_embed_batch_raises_on_error(self, mock_sentence_transformer):
        """Test that exceptions during batch embedding are propagated."""
        service = EmbeddingService()

        mock_sentence_transformer['model'].encode.side_effect = Exception("Batch encoding failed")

        with pytest.raises(Exception, match="Batch encoding failed"):
            service.embed_batch(["test1", "test2"])


class TestGetEmbeddingDimension:
    """Tests for get_embedding_dimension method."""

    def test_get_embedding_dimension(self, mock_sentence_transformer):
        """Test getting the embedding dimension."""
        service = EmbeddingService()

        dimension = service.get_embedding_dimension()

        # Verify the method was called on the model
        mock_sentence_transformer['model'].get_sentence_embedding_dimension.assert_called_once()
        assert dimension == 384
