#!/usr/bin/env bash
set -e

if [ $# -ne 3 ]
    then
        echo "Usage: run_package_manager.sh <volume> <credentials-volume> \"<eric-am-package-manager-arguments>\""
        echo "You must specify the volume, credentials-volume and eric-am-package-manager arguments"
        echo "The eric-am-package-manager arguments must be enclosed in inverted commas"
        echo "The volume is required so that the container has access to the helm chart and you can access the generated csar"
        echo "The credentials-volume is required so that docker in the container has your credentials to pull the images as anonymous pull is being removed"
        echo "Example: run_package_manager.sh /home/myuser/build /home/myuser/.docker/ \"--helm my-helm-chart-0.0.1.tgz --name my-csar\""
        exit 1
fi

volume="${1}"
credentials="${2}"
arguments="${3}"
image="armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:${version:-latest}"
command="docker run --rm -v ${volume}:/csar -v ${credentials}:/root/.docker -v /var/run/docker.sock:/var/run/docker.sock -w /csar ${image} generate ${arguments}"
echo "Docker command which will be run is: ${command}"
echo "..."
eval $command
