import pytest
from pdfstitcher import utils
from pdfstitcher.processing.pagetiler import SW_ROTATION
from pdfstitcher.processing.pagefilter import PageFilter
from pdfstitcher.processing.procbase import ProcessingBase


class TestPageRangeRotation:
    """Test parse_page_range_with_rotation function"""

    def test_simple_page_range(self):
        """Test simple page range without rotation"""
        result = utils.parse_page_range_with_rotation("1,2,3")
        expected = [
            {"page": 1, "rotation": SW_ROTATION.UNSET},
            {"page": 2, "rotation": SW_ROTATION.UNSET},
            {"page": 3, "rotation": SW_ROTATION.UNSET},
        ]
        assert result == expected

    def test_page_range_with_rotation(self):
        """Test page range with rotation"""
        result = utils.parse_page_range_with_rotation("1,2r90,3r180")
        expected = [
            {"page": 1, "rotation": SW_ROTATION.UNSET},
            {"page": 2, "rotation": SW_ROTATION.CLOCKWISE},
            {"page": 3, "rotation": SW_ROTATION.TURNAROUND},
        ]
        assert result == expected

    def test_page_range_with_ranges(self):
        """Test page range with hyphenated ranges"""
        result = utils.parse_page_range_with_rotation("1-3,4r90,5-7r180")
        expected = [
            {"page": 1, "rotation": SW_ROTATION.UNSET},
            {"page": 2, "rotation": SW_ROTATION.UNSET},
            {"page": 3, "rotation": SW_ROTATION.UNSET},
            {"page": 4, "rotation": SW_ROTATION.CLOCKWISE},
            {"page": 5, "rotation": SW_ROTATION.TURNAROUND},
            {"page": 6, "rotation": SW_ROTATION.TURNAROUND},
            {"page": 7, "rotation": SW_ROTATION.TURNAROUND},
        ]
        assert result == expected

    def test_uppercase_rotation(self):
        """Test rotation with uppercase R"""
        result = utils.parse_page_range_with_rotation("1R90,2r180")
        expected = [
            {"page": 1, "rotation": SW_ROTATION.CLOCKWISE},
            {"page": 2, "rotation": SW_ROTATION.TURNAROUND},
        ]
        assert result == expected

    def test_invalid_rotation(self, capsys):
        """Test invalid rotation values"""
        result = utils.parse_page_range_with_rotation("1r45")
        assert result is None
        captured = capsys.readouterr()
        assert "Invalid rotation value: 45" in captured.out

    def test_invalid_format(self, capsys):
        """Test invalid page format"""
        result = utils.parse_page_range_with_rotation("abc")
        assert result is None
        captured = capsys.readouterr()
        assert "Invalid page range format: abc" in captured.out

    def test_empty_range(self, capsys):
        """Test empty page range"""
        result = utils.parse_page_range_with_rotation("")
        assert result is None
        captured = capsys.readouterr()
        assert "Please specify a page range" in captured.out

    def test_all_rotations(self):
        """Test all valid rotation values"""
        result = utils.parse_page_range_with_rotation("1r0,2r90,3r180,4r270,5")
        expected = [
            {"page": 1, "rotation": SW_ROTATION.NONE},
            {"page": 2, "rotation": SW_ROTATION.CLOCKWISE},
            {"page": 3, "rotation": SW_ROTATION.TURNAROUND},
            {"page": 4, "rotation": SW_ROTATION.COUNTERCLOCKWISE},
            {"page": 5, "rotation": SW_ROTATION.UNSET},
        ]
        assert result == expected


class TestRotationUtilities:
    """Test rotation utility functions"""

    def test_degrees_to_sw_rotation(self):
        """Test converting degrees to SW_ROTATION enum"""
        assert SW_ROTATION(0) == SW_ROTATION.NONE
        assert SW_ROTATION(90) == SW_ROTATION.CLOCKWISE
        assert SW_ROTATION(180) == SW_ROTATION.TURNAROUND
        assert SW_ROTATION(270) == SW_ROTATION.COUNTERCLOCKWISE

    def test_invalid_degrees(self):
        """Test invalid degree values"""
        with pytest.raises(ValueError):
            SW_ROTATION(45)

    def test_get_rotation_matrix(self):
        """Test rotation matrix generation"""
        assert utils.get_rotation_matrix(SW_ROTATION.NONE) == [1, 0, 0, 1]
        assert utils.get_rotation_matrix(SW_ROTATION.CLOCKWISE) == [0, -1, 1, 0]
        assert utils.get_rotation_matrix(SW_ROTATION.COUNTERCLOCKWISE) == [0, 1, -1, 0]
        assert utils.get_rotation_matrix(SW_ROTATION.TURNAROUND) == [-1, 0, 0, -1]


class TestProcessingBaseRotation:
    """Test ProcessingBase API changes for rotation"""

    def test_backward_compatibility_list(self, doc_mixed_layers):
        """Test backward compatibility with list of integers"""
        proc = PageFilter(doc=doc_mixed_layers)
        proc.page_range = [1, 2]

        # Should return list of integers for backward compatibility
        assert proc.page_range == [1, 2]

        # Should return full format with rotation
        expected = [{"page": 1, "rotation": 0}, {"page": 2, "rotation": 0}]
        assert proc.page_range_with_rotation == expected

    def test_string_with_rotation(self, doc_mixed_layers):
        """Test string input with rotation"""
        proc = PageFilter(doc=doc_mixed_layers)
        proc.page_range = "1r90,2r180"

        # Should return list of page numbers
        assert proc.page_range == [1, 2]

        # Should return full format with rotation
        expected = [{"page": 1, "rotation": 90}, {"page": 2, "rotation": 180}]
        assert proc.page_range_with_rotation == expected

    def test_page_validation_with_rotation(self, doc_mixed_layers, capsys):
        """Test page validation with rotation format"""
        proc = PageFilter(doc=doc_mixed_layers)
        # doc_mixed_layers has multiple pages
        proc.page_range = "1r90,2,5r180"

        # Page 5 should be removed as out of range
        assert proc.page_range == [1, 2]

        captured = capsys.readouterr()
        assert "Page 5 is out of range" in captured.out
