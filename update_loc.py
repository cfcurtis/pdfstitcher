#! /usr/bin/env python3

if __name__ == '__main__':
    
    from subprocess import run
    from os import listdir
    from os.path import isdir, exists, abspath, dirname
    
    SourceTree = dirname(abspath(__file__))
    T = SourceTree + '/locale/'
    
    run([f'pybabel extract -F babel.cfg -o ./locale/pdfstitcher.pot --copyright-holder="Charlotte Curtis" --project=pdfstitcher .'], shell=True, cwd=SourceTree)

    LOCALES = [lp for lp in listdir(T) if isdir(T+lp)]
    print(LOCALES)

    for L in LOCALES:
        invoke_args = f' -D pdfstitcher -d {T} -i {T}pdfstitcher.pot -l {L}'
        if exists(T+L+'/LC_MESSAGES/pdfstitcher.po'):
            cmd = 'pybabel update' + invoke_args
        else:
            cmd = 'pybabel init' + invoke_args
        run([cmd], shell=True, cwd=SourceTree)

    run([f'pybabel compile -D pdfstitcher -d {T}'], shell=True, cwd=SourceTree)
