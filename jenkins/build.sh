#!/usr/bin/env bash

# Enter the virtualenv
VIRTENV=${WORKSPACE}/.pyenv
. ${VIRTENV}/bin/activate
cd ${WORKSPACE}

# Remove previous builds
rm -rfv ${WORKSPACE}/dist/* || :

# Make a source distribution
if [ -f setup.py ] && [ -f setup.cfg ]; then

    # Get the tag.
    TAG_BUILD=`grep tag_build ${WORKSPACE}/setup.cfg | cut -d'=' -f2 | sed 's/ //g'`

    # If the build is tagged, in any way, then append the Jenkins build number.
    # If the build is not tagged, it is assumed to be a release.
    if [ -n "${TAG_BUILD}" ]; then
        python setup.py egg_info -b ${TAG_BUILD}.${BUILD_NUMBER} sdist
    else
        python setup.py sdist
    fi

    # Create a build record
    SDIST=`ls -1tr ${WORKSPACE}/dist/*.zip | tail -n1`

    LAST_LOG="None"
    if [ -d ${WORKSPACE}/.bzr ]; then
        LAST_LOG=`bzr log -l 1`
    fi

    echo "<html><head><title>${BUILD_TAG}</title></head><body><h2>${BUILD_ID}</h2><ul><li><a href=\"${BUILD_URL}\">${BUILD_TAG}</a></li></ul><h3>Log</h3><pre>${LAST_LOG}</pre></body></html>" > ${SDIST}.html

    # Build sphinx documentation
    if [ -f ${WORKSPACE}/doc/Makefile ]; then
        cd ${WORKSPACE}
        python setup.py build_sphinx
    fi
fi