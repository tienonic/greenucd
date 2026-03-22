import pytest

from src.db import Database


@pytest.fixture
def db():
    """In-memory SQLite database for testing."""
    database = Database()
    yield database
    database.close()
