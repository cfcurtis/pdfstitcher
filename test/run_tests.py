import sys
sys.path.append('..')

from layerfilter import LayerFilter
from tile_pages import PageTiler
from pagefilter import PageFilter
import utils
import pikepdf
import time
import yaml

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("error")

def time_and_test(process,name):
    starttime = time.time()
    print(f'Starting {name}')
    processed = process.run()
    print(f'Process time: {time.time() - starttime:.1f} s')
    return processed

if __name__ == "__main__":
    with open('test_opts.yaml','r') as f:
        test_opts = yaml.safe_load(f)
    
    total_start = time.time()
    for t in test_opts:
        for keep_non_oc in [True,False]:
            non_oc_str = 'with-non-oc' if keep_non_oc else 'without-non-oc'
            print(f"Testing {t['name']} {non_oc_str}")
            in_doc = pikepdf.Pdf.open(t['input'])
            page_range = utils.parse_page_range(t['page_range'])
            if 'layer_filter' in t.keys():
                layer_filter = LayerFilter(in_doc)
                layer_filter.page_range = page_range
                layer_filter.keep_non_oc = keep_non_oc
                for k,v in t['layer_filter'].items():
                    setattr(layer_filter,k,v)
                filtered = time_and_test(layer_filter,t['name'] + ' LayerFilter')
            else:
                filtered = in_doc

            if 'page_tiler' in t.keys():
                page_tiler = PageTiler(filtered)
                page_tiler.page_range = page_range
                for k,v in t['page_tiler'].items():
                    setattr(page_tiler,k,v)
                out_doc = time_and_test(page_tiler,t['name'] + ' PageTiler')
            else:
                page_filter = PageFilter(filtered)
                page_filter.page_range = page_range
                out_doc = time_and_test(page_filter,t['name'] + ' PageFilter')
            
            out_doc.save(f"{t['name']}-{non_oc_str}.pdf",normalize_content=True)
    
    print('...\n...\n...')
    print(f'Total processing time: {time.time() - total_start}')