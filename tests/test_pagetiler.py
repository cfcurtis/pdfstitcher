from pdfstitcher.processing.pagetiler import PageTiler
import pytest

import pdfstitcher.utils as utils


@pytest.fixture(scope="session", autouse=True)
def some_function_name():
    # session setup
    utils.setup_locale()
    yield

    # session teardown


def test_calc_rows_cols():
    """
    Checks a number of configurations of rows and columns
    """
    params = {
        "cols": 6,
        "col_major": True,
    }

    tiler = PageTiler(params=params)

    assert tiler.calc_rows_cols(19) == False
    params["col_major"] = False
    tiler.params = params
    assert tiler.calc_rows_cols(19) == True
