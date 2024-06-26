import pytest
import pdfstitcher.utils as utils
from pdfstitcher.processing.pagetiler import PageTiler
from pdfstitcher.processing.pagefilter import PageFilter
from pdfstitcher.processing.layerfilter import LayerFilter
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
def default_tiler():
    utils.Config.general["units"] = utils.UNITS.INCHES
    params = {
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
    return PageTiler(params=params)


@pytest.fixture
def default_pagefilter():
    return PageFilter(params={"margin": 0})


@pytest.fixture
def default_layerfilter():
    utils.Config.general["units"] = utils.UNITS.INCHES
    params = {
        "keep_ocs": [],
        "line_props": [],
        "keep_non_oc": True,
        "delete_ocgs": True,
    }
    return LayerFilter(params=params)
