#
# COPYRIGHT Ericsson 2024
#
#
#
# The copyright to the computer program(s) herein is the property of
#
# Ericsson Inc. The programs may be used and/or copied only with written
#
# permission from Ericsson Inc. or in accordance with the terms and
#
# conditions stipulated in the agreement/contract under which the
#
# program(s) have been supplied.
#

ARG BASE_IMAGE_VERSION

FROM armdocker.rnd.ericsson.se/proj-am/sles/sles-pm:${BASE_IMAGE_VERSION} as base

ARG HELM2_VERSION="v2.15.1"
ARG HELM3_VERSION="v3.4.2"
ARG HELM3_ADDITIONAL_VERSIONS="v3.5.1 v3.6.3 v3.7.1 v3.8.1 v3.8.2 v3.10.1 v3.10.3 v3.11.3 v3.12.0 v3.13.0"

RUN curl -SsL https://get.helm.sh/helm-${HELM2_VERSION}-linux-amd64.tar.gz | tar xzf - linux-amd64/helm

RUN curl -SsL https://get.helm.sh/helm-${HELM3_VERSION}-linux-amd64.tar.gz -o helm-${HELM3_VERSION}-linux-amd64.tar.gz
RUN mkdir -p linux-amd64-helm3 && tar -zxf helm-${HELM3_VERSION}-linux-amd64.tar.gz -C linux-amd64-helm3

RUN for VERSION in ${HELM3_VERSION} ${HELM3_ADDITIONAL_VERSIONS}; do curl -SsL https://get.helm.sh/helm-${VERSION}-linux-amd64.tar.gz -o helm-${VERSION}-linux-amd64.tar.gz; \
     mkdir -p linux-amd64-helm_${VERSION}; tar -zxf helm-${VERSION}-linux-amd64.tar.gz -C linux-amd64-helm_${VERSION}; \
     mv linux-amd64-helm_${VERSION}/linux-amd64/helm linux-amd64-helm3/linux-amd64/helm_${VERSION/v/}; done

COPY target/eric-am-package-manager.tar.gz .
RUN tar -zxvf eric-am-package-manager.tar.gz

FROM selndocker.mo.sw.ericsson.se/proj-pc-dev/agent-k:3.9 as agent-k

FROM armdocker.rnd.ericsson.se/proj-am/releases/vnfsdk-pkgtools:1.21.0-1 as vnf-pkgtools

COPY --from=base --chown=root:root linux-amd64/helm /usr/local/bin/helm
COPY --from=base --chown=root:root linux-amd64-helm3/linux-amd64/helm /usr/local/bin/helm3
COPY --from=base --chown=root:root linux-amd64-helm3/linux-amd64/helm_* /usr/local/bin/

COPY --from=base eric-am-package-manager .
RUN pip3 install eric_am_package_manager-*.whl
COPY --from=agent-k /usr/bin/agent-k /usr/bin/agent-k

ENTRYPOINT ["eric-am-package-manager"]
