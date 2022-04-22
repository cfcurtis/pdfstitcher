import sys
from pathlib import Path

from pdfstitcher.layerfilter import LayerFilter
from pdfstitcher.tile_pages import PageTiler
from pdfstitcher.pagefilter import PageFilter
import pdfstitcher.utils as utils
import pikepdf
import time
import yaml

if not sys.warnoptions:
    import warnings

    warnings.simplefilter('error')


def time_and_test(process, name):
    starttime = time.time()
    print(f'Starting {name}')
    processed = process.run()
    print(f'Process time: {time.time() - starttime:.1f} s')
    return processed


if __name__ == "__main__":
    root = Path(__file__).parent

    with open(str(root / 'test_opts.yaml'), 'r') as f:
        test_opts = yaml.safe_load(f)

    if len(sys.argv) > 1:
        test_opts = [t for t in test_opts if t['name'] in sys.argv]

    utils.setup_locale()

    total_start = time.time()
    for t in test_opts:
        if sys.platform.startswith('win32'):
            gdrive = 'D:/My Drive/'
        elif sys.platform.startswith('darwin'):
            gdrive = '/Users/cfcurtis/Google Drive'
        elif sys.platform.startswith('linux'):
            gdrive = '/home/charlotte/Documents'

        t['input'] = t['input'].replace('{gdrive}', gdrive)
        t['input'] = t['input'].replace('\\', '/')

        if 'layer_filter' in t.keys():
            if 'keep_non_oc_opts' in t['layer_filter'].keys():
                keep_non_oc_opts = t['layer_filter']['keep_non_oc_opts']
            else:
                keep_non_oc_opts = [True]
            if 'do_fill' in t['layer_filter'].keys():
                do_fill = t['layer_filter']['do_fill']
            else:
                do_fill = [True]
        else:
            keep_non_oc_opts = [True]
            do_fill = [False]

        for keep_non_oc in keep_non_oc_opts:
            for fill in do_fill:
                non_oc_str = 'with-non-oc' if keep_non_oc else 'without-non-oc'
                fill_str = 'with-fill' if fill else 'without-fill'
                print(f"Testing {t['name']} {non_oc_str} {fill_str}")
                try:
                    in_doc = pikepdf.Pdf.open(t['input'])
                except OSError as e:
                    print(e)
                    print('...Skipping')
                
                page_range = utils.parse_page_range(t['page_range'])
                if 'layer_filter' in t.keys():
                    layer_filter = LayerFilter(in_doc)
                    layer_filter.page_range = page_range
                    layer_filter.keep_non_oc = keep_non_oc
                    for k, v in t['layer_filter'].items():
                        setattr(layer_filter, k, v)
                    for key in layer_filter.line_props.keys():
                        layer_filter.line_props[key]['fill_colour'] = fill
                    filtered = time_and_test(layer_filter, t['name'] + ' LayerFilter')
                else:
                    filtered = in_doc

                if 'page_tiler' in t.keys():
                    page_tiler = PageTiler(filtered)
                    page_tiler.page_range = page_range
                    for k, v in t['page_tiler'].items():
                        setattr(page_tiler, k, v)
                    out_doc = time_and_test(page_tiler, t['name'] + ' PageTiler')
                else:
                    page_filter = PageFilter(filtered)
                    page_filter.page_range = page_range
                    out_doc = time_and_test(page_filter, t['name'] + ' PageFilter')

                out_doc.save(f"{t['name']}-{non_oc_str}-{fill_str}.pdf", normalize_content=True)

    print('...\n...\n...')
    print(f'Total processing time: {time.time() - total_start}')
