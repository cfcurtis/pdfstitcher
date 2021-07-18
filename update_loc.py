#! /usr/bin/env python3

if __name__ == '__main__':
    
    from subprocess import run
    from os import listdir
    from os.path import isdir, exists, abspath, dirname, join
    
    SourceTree = dirname(abspath(__file__))
    T = join(SourceTree,'locale')
    
    run(f'pybabel extract -F babel.cfg -o {join(T,"pdfstitcher.pot")} --copyright-holder="Charlotte Curtis" --project=pdfstitcher .', shell=True, cwd=SourceTree)

    LOCALES = [lp for lp in listdir(T) if isdir(join(T,lp))]
    print(LOCALES)

    for L in LOCALES:
        invoke_args = f' -D pdfstitcher -d {T} -i {join(T,"pdfstitcher.pot")} -l {L}'
        if exists(join(T,L,'LC_MESSAGES','pdfstitcher.po')):
            cmd = 'pybabel update' + invoke_args
        else:
            cmd = 'pybabel init' + invoke_args
        run(cmd, shell=True, cwd=SourceTree)

    run(f'pybabel compile -D pdfstitcher -d {T}', shell=True, cwd=SourceTree)
