pybabel extract -F babel.cfg -o locale\pdfstitcher.pot --copyright-holder="Charlotte Curtis" --project=pdfstitcher .
FOR %%L IN (fr_FR,de_DE,nl_NL,es_ES) DO (
    if exist locale\%%L\LC_MESSAGES\pdfstitcher.po (
        pybabel update -D pdfstitcher -d locale -i locale\pdfstitcher.pot -l %%L
    ) else (
        pybabel init -D pdfstitcher -d locale -i locale\pdfstitcher.pot -l %%L
    )
)
pybabel compile -D pdfstitcher -d locale