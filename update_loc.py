#! /usr/bin/env python3

if __name__ == '__main__':
    from subprocess import run
    from os import listdir
    from os.path import isdir, exists, abspath, dirname, join
    import sys
    
    if len(sys.argv) < 2:
        print('Please specify extract, update, compile, or all. For example:')
        print('update_loc.py extract')
        sys.exit()

    SourceTree = dirname(abspath(__file__))
    T = join(SourceTree,'locale')

    if 'extract' in sys.argv or 'all' in sys.argv:
        run(f'pybabel extract -F babel.cfg -o {join(T,"pdfstitcher.pot")} --copyright-holder="Charlotte Curtis" --project=pdfstitcher .', shell=True)

    if 'update' in sys.argv or 'all' in sys.argv:
        LOCALES = [lp for lp in listdir(T) if isdir(join(T,lp))]
        print(LOCALES)

        for L in LOCALES:
            invoke_args = f' -D pdfstitcher -d {T} -i {join(T,"pdfstitcher.pot")} -l {L}'
            if exists(join(T,L,'LC_MESSAGES','pdfstitcher.po')):
                cmd = 'pybabel update' + invoke_args
            else:
                cmd = 'pybabel init' + invoke_args
            run(cmd, shell=True)

    if 'compile' in sys.argv or 'all' in sys.argv:
        run(f'pybabel compile -D pdfstitcher -d locale', shell=True)
