import pytest
import pdfstitcher.utils as utils
from pathlib import Path
from pikepdf import Pdf

TEST_ROOT = Path(__file__).parent
TEST_FILES = TEST_ROOT / "files"


@pytest.fixture
def doc_mixed_layers():
    return Pdf.open(TEST_FILES / "mixed-layers.pdf")


@pytest.fixture(scope="session", autouse=True)
def setup_teardown():
    # session setup
    utils.setup_locale("en")
    yield

    # session teardown


@pytest.fixture
def default_tiler_params():
    return {
        "cols": None,
        "rows": None,
        "col_major": False,
        "right_to_left": False,
        "bottom_to_top": False,
        "rotation": 0,
        "margin": 0,
        "trim": [0, 0, 0, 0],
        "override_trim": False,
        "actually_trim": False,
    }


@pytest.fixture
def default_pagefilter_params():
    return {"margin": 0}
