from pdfstitcher.processing.pagetiler import PageTiler
from pdfstitcher.utils import Config, UNITS


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
