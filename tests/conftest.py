import pytest
from src.wallbot.database.db_helper import DBHelper


@pytest.fixture
def db():
    helper = DBHelper(":memory:")
    helper.setup()
    return helper
