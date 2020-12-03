pybabel extract -o locale/sewingutils.pot --copyright-holder="Charlotte Curtis" --project=sewingutils .
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l fr_FR
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l de_DE
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l nl_NL
pybabel update -D sewingutils -d locale -i locale/sewingutils.pot -l es_ES
pybabel compile -D sewingutils -d locale