from pdfstitcher.processing.pagetiler import PageTiler
from pdfstitcher.utils import Config, UNITS, init_new_doc
import pytest


def test_show_options(capsys, default_tiler):
    """
    Make sure the options are displayed correctly.
    """
    params = default_tiler.params
    params["rows"] = 3
    params["cols"] = 2

    default_tiler._calc_rows_cols(6)
    default_tiler._show_options()

    captured = capsys.readouterr()
    assert "Tiling with {} rows and {} columns".format(default_tiler.rows, default_tiler.cols) in captured.out
    assert "Options:" in captured.out
    assert "Margins: 0 in" in captured.out
    assert "Trim: [0, 0, 0, 0] in" in captured.out
    assert "Rotation: 0" in captured.out
    assert "Page order: Rows then columns, Left to right, Top to bottom" in captured.out

    # add on the alignment parameters
    params["vertical_align"] = "center"
    params["horizontal_align"] = "left"

    default_tiler._show_options()
    captured = capsys.readouterr()
    assert "Vertical alignment: center" in captured.out
    assert "Horizontal alignment: left" in captured.out

    # try with centimetres
    Config.general["units"] = UNITS.CENTIMETERS
    default_tiler._show_options()
    captured = capsys.readouterr()
    assert "Margins: 0 cm" in captured.out

def test_update_units(doc_mixed_layers, default_tiler):
    """
    Test updating the units.
    """
    default_tiler.load_doc(doc_mixed_layers)
    default_tiler.page_range = None
    default_tiler._update_units()
    assert default_tiler.output_uu == pytest.approx(10.0)

def test_get_trim(default_tiler, doc_mixed_layers):
    """
    Test getting the trim values in various units.
    """
    default_tiler.params["trim"] = [1, 1, 1, 1]
    default_tiler.load_doc(doc_mixed_layers)
    default_tiler.page_range = None
    default_tiler._update_units()
    assert default_tiler._get_trim(default_tiler.output_uu) == [pytest.approx(7.2)] * 4

    Config.general["units"] = UNITS.CENTIMETERS
    default_tiler._update_units()
    assert default_tiler._get_trim(default_tiler.output_uu) == [pytest.approx(7.2/2.54)] * 4

def test_get_first_page_dims(doc_mixed_layers, default_tiler):
    """
    Test getting the dimensions of the first page.
    """
    default_tiler.load_doc(doc_mixed_layers)
    default_tiler.page_range = [1]
    default_tiler._update_units()
    dims = default_tiler._get_first_page_dims()
    assert dims == (pytest.approx(1800.0), pytest.approx(1800.0))

    # second page only
    default_tiler.page_range = [2]
    default_tiler._update_units()
    dims = default_tiler._get_first_page_dims()
    assert dims == (pytest.approx(14400.0), pytest.approx(14400.0))

def test_process_page(doc_mixed_layers, default_tiler):
    """
    Test the page processing. Relies on previous functions.
    """
    # mixed_layers document has two pages with different UserUnits
    default_tiler.load_doc(doc_mixed_layers)
    default_tiler.out_doc = init_new_doc(default_tiler.in_doc)
    default_tiler.page_range = [1, 2]
    default_tiler._update_units()
    content_dict = {}
    info = []
    default_tiler._process_page(content_dict, 1, info)
    pagekey = info[-1]["pagekey"]
    assert pagekey == f"/Page{1}"
    assert pagekey in content_dict
    assert info[-1]["width"] == pytest.approx(1800.0)
    assert float(content_dict[pagekey].Matrix[0]) == pytest.approx(1.0)

    # second time a given page should not be re-added
    default_tiler._process_page(content_dict, 1, info)
    assert len(content_dict) == 1
    assert len(info) == 1

    # test with a different page
    default_tiler._process_page(content_dict, 2, info)
    pagekey = info[-1]["pagekey"]
    assert pagekey == f"/Page{2}"
    assert pagekey in content_dict
    assert content_dict[pagekey].BBox == default_tiler.in_doc.pages[1].MediaBox
    assert float(content_dict[pagekey].Matrix[0]) == pytest.approx(0.1)

    # now try with trim values
    default_tiler.params["trim"] = [10, 10, 10, 10]
    default_tiler.params["actually_trim"] = True
    default_tiler._update_units()
    content_dict = {}
    info = []
    default_tiler._process_page(content_dict, 1, info)
    assert info[-1]["width"] == pytest.approx(1656.0)
    assert info[-1]["height"] == pytest.approx(1656.0)
    
    default_tiler._process_page(content_dict, 2, info)
    assert info[-1]["width"] == pytest.approx(1296.0)
    assert info[-1]["height"] == pytest.approx(1296.0)

def test_build_pagelist(default_tiler, doc_mixed_layers):
    """
    Test building the page list.
    """
    # Test with no document
    assert default_tiler._build_pagelist() is None

    # load the mixed layers document
    default_tiler.load_doc(doc_mixed_layers)
    default_tiler.out_doc = init_new_doc(default_tiler.in_doc)
    
    page_ranges = [None, [1, 1], [1, 2], [1, 3]]
    expected_lengths = [2, 1, 2, 1]

    for page_range, expected_length in zip(page_ranges, expected_lengths):
        default_tiler.page_range = page_range
        default_tiler._update_units()
        content_dict, info = default_tiler._build_pagelist()
        assert len(content_dict) == expected_length
        assert len(info) == expected_length
        assert all(i["pagekey"] in content_dict for i in info)
    
    # zeros need a bit of different handling
    default_tiler.page_range = [0, 1]
    default_tiler._update_units()
    content_dict, info = default_tiler._build_pagelist()
    assert len(content_dict) == 1
    assert len(info) == 2
    assert info[0]["pagekey"] is None
    assert info[1]["pagekey"] in content_dict
    assert info[0]["width"] == info[1]["width"]

    # other way around
    default_tiler.page_range = [1, 0]
    default_tiler._update_units()
    content_dict, info = default_tiler._build_pagelist()
    assert len(content_dict) == 1
    assert len(info) == 2
    assert info[1]["pagekey"] is None
    assert info[0]["pagekey"] in content_dict
    assert info[0]["width"] == info[1]["width"]

def test_calc_rows_cols(default_tiler):
    """
    Checks a number of configurations of rows and columns.
    """
    # no cols, no rows, 0 tiles
    assert default_tiler._calc_rows_cols(0) == False

    # calculate a square
    assert default_tiler._calc_rows_cols(25) == True

    # 3 x 6 = 18 no matter how you slice it
    for set_rows in [False, True]:
        for col_major in [False, True]:
            if set_rows:
                default_tiler.params["rows"] = 3
                default_tiler.params["cols"] = None
            else:
                default_tiler.params["rows"] = None
                default_tiler.params["cols"] = 6
            default_tiler.params["col_major"] = col_major
            assert default_tiler._calc_rows_cols(18) == True

    # However 6 cols and 19 pages does weird stuff
    default_tiler.params["cols"] = 6
    default_tiler.params["col_major"] = False
    assert default_tiler._calc_rows_cols(19) == True
    default_tiler.params["col_major"] = True
    assert default_tiler._calc_rows_cols(19) == False
