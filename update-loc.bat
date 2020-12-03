pybabel extract -o locale/sewingutils.pot --copyright-holder="Charlotte Curtis" --project=sewingutils .
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l fr_FR
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l de_DE
pybabel compile -D sewingutils -d locale