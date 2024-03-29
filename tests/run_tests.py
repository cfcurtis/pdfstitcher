import sys
from pathlib import Path

from pdfstitcher.layerfilter import LayerFilter
from pdfstitcher.tile_pages import PageTiler
from pdfstitcher.pagefilter import PageFilter
import pdfstitcher.utils as utils
import pikepdf
import time
import yaml
import cProfile, pstats

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("error")


def time_and_test(process, name, full_profile=False):
    if full_profile:
        return profile(process, name)

    starttime = time.time()
    print(f"Starting {name}")
    processed = process.run()
    print(f"Process time: {time.time() - starttime:.1f} s")
    return processed


def profile(process, name):
    print(f"Profiling {name}")
    with cProfile.Profile() as pr:
        processed = process.run()
        stats = pstats.Stats(pr).sort_stats("cumulative")
        stats.print_stats()
    return processed


if __name__ == "__main__":
    root = Path(__file__).parent

    with open(str(root / "test_opts.yaml"), "r") as f:
        test_opts = yaml.safe_load(f)

    if len(sys.argv) > 1:
        test_opts = [t for t in test_opts if t["name"] in sys.argv]

    utils.setup_locale()

    total_start = time.time()
    for t in test_opts:
        if sys.platform.startswith("win32"):
            gdrive = "C:/Users/ccurtis/Documents"
        elif sys.platform.startswith("darwin"):
            gdrive = "/Users/charlotte/Documents"
        elif sys.platform.startswith("linux"):
            gdrive = str(Path.home() / "gdrive/personal")

        t["input"] = t["input"].replace("{gdrive}", gdrive)
        t["input"] = t["input"].replace("\\", "/")

        if "layer_filter" in t.keys():
            if "keep_non_oc_opts" in t["layer_filter"].keys():
                keep_non_oc_opts = t["layer_filter"]["keep_non_oc_opts"]
            else:
                keep_non_oc_opts = [True]
            if "do_fill" in t["layer_filter"].keys():
                do_fill = t["layer_filter"]["do_fill"]
            else:
                do_fill = [True]
        else:
            keep_non_oc_opts = [True]
            do_fill = [False]

        for keep_non_oc in keep_non_oc_opts:
            for fill in do_fill:
                non_oc_str = "with-non-oc" if keep_non_oc else "without-non-oc"
                fill_str = "with-fill" if fill else "without-fill"
                print(f"Testing {t['name']} {non_oc_str} {fill_str}")
                try:
                    in_doc = pikepdf.Pdf.open(t["input"])
                except OSError as e:
                    print(e)
                    print("...Skipping")
                    continue

                page_range = utils.parse_page_range(t["page_range"])
                if "layer_filter" in t.keys():
                    layer_filter = LayerFilter(in_doc)
                    layer_filter.page_range = page_range
                    layer_filter.keep_non_oc = keep_non_oc
                    for k, v in t["layer_filter"].items():
                        if k == "line_props" and "all" in v.keys():
                            continue
                        setattr(layer_filter, k, v)

                    if (
                        "line_props" in t["layer_filter"].keys()
                        and "all" in t["layer_filter"]["line_props"].keys()
                    ):
                        layers = layer_filter.get_layer_names()
                        for layer in layers:
                            for k, v in t["layer_filter"]["line_props"]["all"].items():
                                layer_filter.line_props[layer] = {}
                                layer_filter.line_props[layer][k] = v

                    for key in layer_filter.line_props.keys():
                        layer_filter.line_props[key]["fill_colour"] = fill

                    full_profile = (
                        "profile" in t["layer_filter"].keys() and t["layer_filter"]["profile"]
                    )
                    filtered = time_and_test(layer_filter, t["name"] + " LayerFilter", full_profile)
                else:
                    filtered = in_doc

                if "page_tiler" in t.keys():
                    page_tiler = PageTiler(filtered)
                    page_tiler.page_range = page_range
                    for k, v in t["page_tiler"].items():
                        setattr(page_tiler, k, v)
                    full_profile = (
                        "profile" in t["page_tiler"].keys() and t["page_tiler"]["profile"]
                    )
                    out_doc = time_and_test(page_tiler, t["name"] + " PageTiler", full_profile)
                else:
                    page_filter = PageFilter(filtered)
                    page_filter.page_range = page_range
                    out_doc = time_and_test(page_filter, t["name"] + " PageFilter")

                out_doc.save(f"{t['name']}-{non_oc_str}-{fill_str}.pdf", normalize_content=True)

    print("...\n...\n...")
    print(f"Total processing time: {time.time() - total_start}")
