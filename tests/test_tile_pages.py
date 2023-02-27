from pdfstitcher.tile_pages import PageTiler


def test_calc_rows_cols():
    """Checks a number of configurations of rows and columns"""

    tiler = PageTiler()
    tiler.cols = 6
    tiler.col_major = True

    assert tiler.calc_rows_cols(19) == False
    tiler.col_major = False
    assert tiler.calc_rows_cols(19) == True
