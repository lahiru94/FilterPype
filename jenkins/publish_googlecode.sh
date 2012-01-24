#!/usr/bin/env bash

# Enter the virtualenv
. ${VIRTENV}/bin/activate
cd ${WORKSPACE}

# Add Google authentication credentials
if [ -e ~/.netrc ]; then
    grep "machine code.google.com login flexiondotorg@gmail.com password fZ5PQ5cw4sC6" ~/.netrc || :

    if [ $? -eq 1 ]; then
        echo "machine code.google.com login flexiondotorg@gmail.com password fZ5PQ5cw4sC6" >> ~/.netrc
    fi
else
    echo "machine code.google.com login flexiondotorg@gmail.com password fZ5PQ5cw4sC6" > ~/.netrc
fi


mkdir -p /tmp/bzr2git/FilterPype || :
cd /tmp/bzr2git/FilterPype

# Get Bazaar code
if [ ! -d FilterPype.bzr ]; then
    bzr branch http://vindictive.flightdataservices.com/Bazaar/FilterPype/ FilterPype.bzr || :
else
    cd FilterPype.bzr
    bzr pull
    cd ..
fi

# Get Git code
if [ ! -d FilterPype.git ]; then
    git clone https://code.google.com/p/filterpype/ FilterPype.git || :
else
    cd FilterPype.git
    git pull
    cd ..
fi

cd /tmp/bzr2git/FilterPype/FilterPype.git
bzr fast-export --export-marks /tmp/bzr2git/FilterPype/FilterPype.marks /tmp/bzr2git/FilterPype/FilterPype.bzr | git fast-import || :
git push || :