#!/usr/bin/env bash

# Enter the virtualenv
. ${VIRTENV}/bin/activate
cd ${WORKSPACE}

# Remove previous builds
rm -rfv ${WORKSPACE}/dist/* || :

# Make a source distribution
if [ -f setup.py ]; then
    TAG_BUILD=`grep tag_build ${WORKSPACE}/setup.cfg | cut -d'=' -f2 | sed 's/ //g'`

    # If the build is tagged, in any way, then append the Jenkins build number.
    # If the build is not tagged, it is assumed to be a release.
    if [ -n "${TAG_BUILD}" ]; then
        python setup.py egg_info -b ${TAG_BUILD}.${BUILD_NUMBER} sdist
    else
        python setup.py sdist
    fi
fi

# Build sphinx documentation
if [ -f doc/Makefile ]; then
    cd ${WORKSPACE}
    python setup.py build_sphinx
fi