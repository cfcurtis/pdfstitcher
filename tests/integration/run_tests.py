import sys
from pathlib import Path

from pdfstitcher.processing.mainproc import MainProcess
import pdfstitcher.utils as utils
import pikepdf
import time
import yaml
import cProfile, pstats

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("error")


def time_and_test(process: MainProcess, name: str, full_profile=False) -> None:
    if full_profile:
        profile(process, name)
    else:
        starttime = time.time()
        print(f"Starting {name}")
        process.run()
        print(f"Process time: {time.time() - starttime:.1f} s")


def profile(process: MainProcess, name: str):
    print(f"Profiling {name}")
    with cProfile.Profile() as pr:
        process.run()
        stats = pstats.Stats(pr).sort_stats("cumulative")
        stats.print_stats()


def complete_filename(t: dict) -> None:
    if sys.platform.startswith("win32"):
        gdrive = "C:/Users/ccurtis/Documents"
    elif sys.platform.startswith("darwin"):
        gdrive = "/Users/charlotte/Documents"
    elif sys.platform.startswith("linux"):
        gdrive = str(Path.home() / "gdrive/personal")

    if "{gdrive}" in t["input"]:
        t["input"] = t["input"].replace("{gdrive}", gdrive)
    else:
        # assume it's in files
        t["input"] = str(root.parent / "files" / t["input"])

    t["input"] = t["input"].replace("\\", "/")


if __name__ == "__main__":
    root = Path(__file__).parent

    with open(str(root / "test_opts.yaml"), "r") as f:
        test_opts = yaml.safe_load(f)

    if len(sys.argv) > 1:
        test_opts = [t for t in test_opts if t["name"] in sys.argv]

    utils.setup_locale()

    total_start = time.time()

    # reuse the same main process to make sure that works
    main_process = MainProcess()

    for t in test_opts:
        complete_filename(t)

        # if "layer_filter" in t.keys():
        #     if "keep_non_oc_opts" in t["layer_filter"].keys():
        #         keep_non_oc_opts = t["layer_filter"]["keep_non_oc_opts"]
        #     else:
        #         keep_non_oc_opts = [True]
        #     if "do_fill" in t["layer_filter"].keys():
        #         do_fill = t["layer_filter"]["do_fill"]
        #     else:
        #         do_fill = [True]
        # else:
        #     keep_non_oc_opts = [True]
        #     do_fill = [False]

        # default params
        tile_params = {
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

        # for keep_non_oc in keep_non_oc_opts:
        #     for fill in do_fill:
        # non_oc_str = "with-non-oc" if keep_non_oc else "without-non-oc"
        # fill_str = "with-fill" if fill else "without-fill"
        non_oc_str = "no-layer-filter"
        fill_str = ""

        print(f"Testing {t['name']} {non_oc_str} {fill_str}")
        try:
            main_process.load_doc(t["input"])
        except OSError as e:
            print(e)
            print("...Skipping")
            continue

        main_process.page_range = t["page_range"]
        if "layer_filter" in t.keys():
            print("Layer filter not yet implemented, skipping layer processing")

            # main_process.toggle("LayerFilter", True)
            # main_process.set_params("LayerFilter", t["layer_filter"])
            # for k, v in t["layer_filter"].items():
            #     if k == "line_props" and "all" in v.keys():
            #         continue
            #     setattr(layer_filter, k, v)

            # if (
            #     "line_props" in t["layer_filter"].keys()
            #     and "all" in t["layer_filter"]["line_props"].keys()
            # ):
            #     layers = layer_filter.get_layer_names()
            #     for layer in layers:
            #         for k, v in t["layer_filter"]["line_props"]["all"].items():
            #             layer_filter.line_props[layer] = {}
            #             layer_filter.line_props[layer][k] = v

            # for key in layer_filter.line_props.keys():
            #     layer_filter.line_props[key]["fill_colour"] = fill

            # full_profile = (
            #     "profile" in t["layer_filter"].keys() and t["layer_filter"]["profile"]
            # )
            # filtered = time_and_test(layer_filter, t["name"] + " LayerFilter", full_profile)

        if "page_tiler" in t.keys():
            main_process.toggle("PageTiler", True)
            for k, v in t["page_tiler"].items():
                tile_params[k] = v
            main_process.set_params("PageTiler", tile_params)
            full_profile = "profile" in t["page_tiler"].keys() and t["page_tiler"]["profile"]
        else:
            main_process.toggle("PageFilter", True)
            main_process.set_params("PageFilter", {"margin": 0})

        try:
            time_and_test(main_process, t["name"] + " PageTiler", full_profile)
        except Exception as e:
            print(f"Error! {e}")
            print("...Skipping")
            continue

        outname = root / f"{t['name']}-{non_oc_str}-{fill_str}.pdf"
        main_process.out_doc.save(outname, normalize_content=True)

    print("...\n...\n...")
    print(f"Total processing time: {time.time() - total_start}")
