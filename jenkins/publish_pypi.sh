#!/usr/bin/env bash

TAG_BUILD=`grep tag_build ${WORKSPACE}/setup.cfg | cut -d'=' -f2 | sed 's/ //g'`

# If the build is tagged, in any way, it will not be published on PyPI
if [ -n "${TAG_BUILD}" ]; then
    # Publish to PyPI
    echo "[distutils]"                 >  ~/.pypirc
    echo "index-servers ="             >> ~/.pypirc
    echo "    pypi"                    >> ~/.pypirc
    echo ""                            >> ~/.pypirc
    echo "[pypi]"                      >> ~/.pypirc
    echo "username:flightdataservices" >> ~/.pypirc
    echo "password:open1eye"           >> ~/.pypirc
    python setup.py sdist upload
    python setup.py upload_sphinx
fi