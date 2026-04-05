from pathlib import Path
import tempfile

import pytest


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)
