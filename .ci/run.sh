#!/usr/bin/env bash

if [ "$2" = "2" ]; then
    echo "run python-nxstools"
    docker exec ndts /bin/bash -c 'export DISPLAY=":99.0"; python test'
else
    echo "run python3-nxstools"
    if [ "$1" = "debian10" ] || [ "$1" = "ubuntu22.04" ] || [ "$1" = "ubuntu24.04" ] || [ "$1" = "ubuntu24.10" ] || [ "$1" = "ubuntu23.10" ] || [ "$1" = "ubuntu20.04" ] || [ "$1" = "ubuntu20.10" ] || [ "$1" = "debian11" ]  || [ "$1" = "debian12" ]  || [ "$1" = "debian12tg10" ] ; then
	docker exec ndts python3 -m pytest --cov=nxstools --cov-report=term-missing test
    else
	if [ "$1" = "debian9" ]; then
	    docker exec ndts /bin/bash -c 'export DISPLAY=":99.0"; python3 test'
	else
	    docker exec ndts python3 test
	fi
    fi
fi    
if [ "$?" != "0" ]; then exit 255; fi
