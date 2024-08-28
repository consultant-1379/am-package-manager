# ******************************************************************************
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
# ******************************************************************************
'''Docker image classes'''


class Image:
    """Holds information about a docker image.
        repo is mandatory, tag is optional"""

    def __init__(self, repo, tag='latest'):
        self.repo = repo
        self.tag = tag

    def __str__(self):
        return self.repo + ":" + self.tag

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        if isinstance(other, Image):
            return self.__str__() == other.__str__()
        return False
