from pdfstitcher.processing.pagetiler import PageTiler
from pdfstitcher.utils import Config, UNITS, init_new_doc


def test_show_options(capsys, default_tiler_params):
    """
    Make sure the options are displayed correctly.
    """
    params = default_tiler_params
    params["rows"] = 3
    params["cols"] = 2

    tiler = PageTiler(params=params)
    tiler._calc_rows_cols(6)
    tiler._show_options()

    captured = capsys.readouterr()
    assert "Tiling with {} rows and {} columns".format(tiler.rows, tiler.cols) in captured.out
    assert "Options:" in captured.out
    assert "Margins: 0 in" in captured.out
    assert "Trim: [0, 0, 0, 0] in" in captured.out
    assert "Rotation: 0" in captured.out
    assert "Page order: Rows then columns, Left to right, Top to bottom" in captured.out

    # add on the alignment parameters
    params["vertical_align"] = "center"
    params["horizontal_align"] = "left"

    tiler._show_options()
    captured = capsys.readouterr()
    assert "Vertical alignment: center" in captured.out
    assert "Horizontal alignment: left" in captured.out

    # try with centimetres
    Config.general["units"] = UNITS.CENTIMETERS
    tiler._show_options()
    captured = capsys.readouterr()
    assert "Margins: 0 cm" in captured.out


def test_process_page(doc_mixed_layers, default_tiler_params):
    # mixed_layers document has two pages with different UserUnits
    params = default_tiler_params
    params["rows"] = 1
    tiler = PageTiler(doc=doc_mixed_layers, params=params)
    tiler.out_doc = init_new_doc(tiler.in_doc)
    tiler.page_range = [1, 2]
    tiler._update_units()
    content_dict = {}
    pagekey = tiler._process_page(content_dict, 1)
    assert pagekey == f"/Page{1}"
    assert pagekey in content_dict

    # second time a given page should not be re-added
    assert tiler._process_page(content_dict, 1) is None


# Start auto-added by copilot
def test_build_pagelist(default_tiler_params):
    """
    Test building the page list.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # Test with single page
    tiler.page_range = [1]
    pagelist = tiler._build_pagelist()
    assert pagelist == [1]

    # Test with multiple pages
    tiler.page_range = [1, 2, 3]
    pagelist = tiler._build_pagelist()
    assert pagelist == [1, 2, 3]

    # Test with page range
    tiler.page_range = [1, 3, 5]
    pagelist = tiler._build_pagelist()
    assert pagelist == [1, 3, 5]


def test_adjust_trim_order(default_tiler_params):
    """
    Test adjusting the trim order.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # Test with default trim order
    tiler._adjust_trim_order()
    assert tiler.trim_order == [0, 1, 2, 3]

    # Test with custom trim order
    params["trim_order"] = [3, 2, 1, 0]
    tiler = PageTiler(params=params)
    tiler._adjust_trim_order()
    assert tiler.trim_order == [3, 2, 1, 0]


def test_grid_position(default_tiler_params):
    """
    Test calculating the grid position.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # Test with single column
    tiler.cols = 1
    position = tiler._grid_position(0)
    assert position == (0, 0)

    # Test with multiple columns
    tiler.cols = 3
    position = tiler._grid_position(4)
    assert position == (1, 1)


def test_calc_shift(default_tiler_params):
    """
    Test calculating the shift.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # Test with equal horizontal and vertical space
    shift = tiler._calc_shift(10, 10)
    assert shift == (5, 5)

    # Test with different horizontal and vertical space
    shift = tiler._calc_shift(15, 10)
    assert shift == (7.5, 5)


def test_update_units(default_tiler_params):
    """
    Test updating the units.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # Test with default units
    tiler._update_units()
    assert tiler.units == "in"

    # Test with custom units
    Config.general["units"] = UNITS.CENTIMETERS
    tiler._update_units()
    assert tiler.units == "cm"


# Add more tests here...


def test_calc_rows_cols(default_tiler_params):
    """
    Checks a number of configurations of rows and columns.
    """
    params = default_tiler_params
    tiler = PageTiler(params=params)

    # no cols, no rows, 0 tiles
    assert tiler._calc_rows_cols(0) == False

    # calculate a square
    assert tiler._calc_rows_cols(25) == True

    # 3 x 6 = 18 no matter how you slice it
    for set_rows in [False, True]:
        for col_major in [False, True]:
            if set_rows:
                params["rows"] = 3
                params["cols"] = None
            else:
                params["rows"] = None
                params["cols"] = 6
            params["col_major"] = col_major
            assert tiler._calc_rows_cols(18) == True

    # However 6 cols and 19 pages does weird stuff
    params["cols"] = 6
    params["col_major"] = False
    assert tiler._calc_rows_cols(19) == True
    params["col_major"] = True
    assert tiler._calc_rows_cols(19) == False
