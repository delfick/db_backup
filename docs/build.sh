#!/bin/bash

# use with --help to get information
for ARG in $*; do
    if [ $ARG = "--help" -o $ARG = "-h" ]; then
        echo "Script to build the documentation"
        echo "Use with --clean if you edit anything in support"
        echo ", otherwise those changes won't be built by non changed documentation"
        exit 0
    fi
done

# use with --clean if you change anything in support
if [[ $1 = "--clean" ]]; then
    rm -rf _build
fi

sphinx-build -b html -d _build/doctrees docs _build/html
