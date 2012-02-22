#!/usr/bin/env bash

# Enter the virtualenv
VIRTENV=${WORKSPACE}/.pyenv
. ${VIRTENV}/bin/activate
cd ${WORKSPACE}

# Get the tag.
TAG_BUILD=`grep tag_build ${WORKSPACE}/setup.cfg | cut -d'=' -f2 | sed 's/ //g'`

# If the build is tagged, in any way, it will not be published on PyPI
if [ -n "${TAG_BUILD}" ]; then
    echo "This build is tagged : ${TAG_BUILD}"
    echo "Therefore it will NOT be published on PyPI"
else    
    if [ -e ~/.pypirc ]; then
        # Publish to PyPI
        python setup.py sdist upload
        python setup.py upload_sphinx
    else
        echo "This build is a release, but there is no '~/.pypirc' which"
        echo "should look something like this"
        echo
        echo "[distutils]"
        echo "index-servers ="
        echo "    pypi"
        echo
        echo "[pypi]"
        echo "username:yourusername"
        echo "password:yourpssword"
    fi
fi
