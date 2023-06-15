from pathlib import Path

import pytest


@pytest.fixture
def sample_basic_puls_file():
    return Path(__file__).parent / "data" / "sample_basic.puls"


@pytest.fixture
def sample_with_ext2_file():
    return Path(__file__).parent / "data" / "sample_with_ext2.puls"
