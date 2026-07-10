import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# Garante import de modulos do projeto via "src." durante os testes.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Defaults de ambiente para evitar dependencias externas em testes.
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def app_client():
    """Client de app com bootstrap de banco neutralizado para testes."""
    with patch("src.main.Base.metadata.create_all"):
        from src.main import app

    return TestClient(app)
