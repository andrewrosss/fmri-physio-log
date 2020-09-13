from pathlib import Path

import pytest


@pytest.fixture
def sample_puls_file():
    return Path(__file__).parent / "data" / "sample.puls"
