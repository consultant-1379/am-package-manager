#!/usr/bin/env bash
set -e

[ "$IMAGE_AM_PACKAGE_MANAGER" ] || IMAGE_AM_PACKAGE_MANAGER="armdocker.rnd.ericsson.se/proj-am/releases/eric-am-package-manager:2.60.0"
[ "$IMAGE_AGENTK" ] || IMAGE_AGENTK="selndocker.mo.sw.ericsson.se/proj-pc-dev/agent-k:3.3"
[ "$DOCKER_CONFIG" ] || DOCKER_CONFIG="${HOME}/.docker"

usage() {
	cat << EOF 1>&2
Usage: $0 chart.tgz [am-package-manager-options]
EOF
	exit 1
}

msg() {
	echo "$*" 1>&2
}

[ "$1" ] || usage

chart_pkg=$1
chart_name=$(echo "$chart_pkg" | sed 's/\.tgz$//')
chart_images="${chart_name}-docker.tar"
shift

docker_config_arg=""
if [ -d "$DOCKER_CONFIG" ] ; then
	docker_config_arg="-v $DOCKER_CONFIG:${HOME}/.docker"
else
	msg "WARNING: Docker credentials not found, fallback to anonymous access"
fi

pwd=$(pwd)

msg "Download docker images referred to by '$chart_pkg' ..."
docker run --rm --init --user "$(id -u):$(id -g)" --env HOME --volume "${pwd}:${pwd}" $docker_config_arg --workdir "$pwd" "$IMAGE_AGENTK" \
	export --always-true --output="${chart_images}" "$chart_pkg"

msg "Create CSAR package ..."
docker run --rm --init --user "$(id -u):$(id -g)" --env HOME --volume "${pwd}:${pwd}" $docker_config_arg --workdir "$pwd" "$IMAGE_AM_PACKAGE_MANAGER" \
	generate --name "$chart_name" --helm "$chart_pkg" --images "$chart_images" "$@"
