#!/usr/bin/env bash

echo "install pixi"
docker exec  ndts /bin/bash -c 'curl -fsSL https://pixi.sh/install.sh | sh ; export PATH=/var/lib/tango/.pixi/bin:$PATH ; pixi shell-hook  --manifest-path .github/workflows/pixi/pixi.toml > .sh.sh ; source .sh.sh ; pixi add  --manifest-path .github/workflows/pixi/pixi.toml rattler-build'
# docker exec  ndts /bin/bash -c 'curl -fsSL https://pixi.sh/install.sh | sh ; export PATH=/var/lib/tango/.pixi/bin:$PATH ; pixi shell-hook  --manifest-path .github/workflows/pixi/pixi.toml > .sh.sh ; source .sh.sh ; pixi add  --manifest-path .github/workflows/pixi/pixi.toml rattler-build nxsconfigserver-db'
# # /home/tango
# docker exec  ndts /bin/bash -c 'pwd '
# # /var/lib/tango
# docker exec  ndts /bin/bash -c 'echo "$HOME" '

# # create nxsconfig database
# docker exec  --user root ndts /bin/bash -c 'source /home/tango/.sh.sh ; export MYSQL_PASSWORD="rootpw" ; create_nxsconfig_db -x -d=nxsonfig -u=tango -p="$CONDA_PREFIX"'

echo "run nxsconfigserver-db"
docker exec  ndts /bin/bash -c 'source .sh.sh ; pixi run  --manifest-path .github/workflows/pixi/pixi.toml rattler-build build  --recipe .github/workflows/pixi/recipe.yaml'

ERROR=$?
if [ $ERROR -ne "0" ]
then
    echo "ERROR "$ERROR
    exit 255
fi
