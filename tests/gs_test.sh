# env /bin/bash
echo "Running gs on all pdfs in tests folder..."
for pdf in *.pdf; do
    gs -dNOPAUSE -dBATCH -sDEVICE=nullpage "$pdf" | grep -i 'warn\|err'
done
echo "Done"