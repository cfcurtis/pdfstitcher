"""
Regression tests for the exception handlers in
``LayerFilter._process_content``.

The original bug had two ``except`` blocks that called ``.format(...)``
on the return value of ``print(...)`` (which is ``None``), e.g.::

    print("Failed writing stream to page with error type {}").format(type(e))

This raised ``AttributeError: 'NoneType' object has no attribute 'format'``
whenever the underlying try block actually failed, completely masking
the original error and aborting the layer filter run.

These tests force the two failure paths to fire and confirm:
1. No ``AttributeError`` (the original bug) is raised.
2. The diagnostic message is printed and contains the exception type name.
"""

import pikepdf
import pytest


def _reset_for_reprocess(layerfilter):
    """
    ``LayerFilter.run()`` populates ``processed_objects`` and ``current_state``.
    To call ``_process_content`` again on a page we need a clean slate, otherwise
    the early-return guard at the top of ``_process_content`` short-circuits.
    """
    layerfilter.processed_objects = set()
    layerfilter.pdf_line_props = {}
    layerfilter.user_unit = 1
    layerfilter._initialize_state()


def test_unparse_failure_does_not_raise_attribute_error(
    monkeypatch, capsys, doc_mixed_layers, default_layerfilter
):
    """
    When ``pikepdf.unparse_content_stream`` raises during ``_process_content``,
    the except block must print a diagnostic instead of crashing with
    ``AttributeError`` (the original bug) or any other exception.
    """
    default_layerfilter.load_doc(doc_mixed_layers)
    default_layerfilter.page_range = None
    assert default_layerfilter.run() is True

    _reset_for_reprocess(default_layerfilter)

    def boom(*args, **kwargs):
        raise RuntimeError("simulated unparse failure")

    monkeypatch.setattr(pikepdf, "unparse_content_stream", boom)

    page = default_layerfilter.out_doc.pages[0]

    try:
        default_layerfilter._process_content(page, do_filter=True)
    except AttributeError as exc:
        pytest.fail(f"Original bug regressed - AttributeError raised: {exc}")

    captured = capsys.readouterr()
    assert "Failed writing stream to page" in captured.out
    assert "RuntimeError" in captured.out


def test_write_failure_does_not_raise_attribute_error(
    monkeypatch, capsys, doc_mixed_layers, default_layerfilter
):
    """
    When ``out_doc.make_stream`` raises during the final write step of
    ``_process_content``, the except block must print a diagnostic instead
    of crashing with ``AttributeError`` (the original bug).
    """
    default_layerfilter.load_doc(doc_mixed_layers)
    default_layerfilter.page_range = None
    assert default_layerfilter.run() is True

    _reset_for_reprocess(default_layerfilter)

    def boom(*args, **kwargs):
        raise ValueError("simulated make_stream failure")

    monkeypatch.setattr(default_layerfilter.out_doc, "make_stream", boom)

    page = default_layerfilter.out_doc.pages[0]

    try:
        default_layerfilter._process_content(page, do_filter=True)
    except AttributeError as exc:
        pytest.fail(f"Original bug regressed - AttributeError raised: {exc}")

    captured = capsys.readouterr()
    assert "Failed writing stream to page" in captured.out
    assert "ValueError" in captured.out
