# env /bin/bash
pdfs=`ls *.pdf`
if [[ $# -eq 0 ]] ; then
    echo "Running gs on all pdfs in tests folder"
else
    pdfs="$@"
fi

for pdf in $pdfs; do
    echo "Checking $pdf..."
    gs -dNOPAUSE -dBATCH -sDEVICE=nullpage "$pdf" | grep -i 'warn\|err'
done
echo "Done"
