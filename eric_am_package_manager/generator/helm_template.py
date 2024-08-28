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
'''Helm template class'''

import logging
# pylint: disable=import-error
import yaml

from .utils import collect_values_of_key_by_type


class HelmTemplate:
    """This class contains methods for retrieving information from the rendered chart."""

    def __init__(self, helm_template):
        self.templates = self.__load_into_yaml(helm_template)

    def get_images(self):
        """Get all images

        :return: List of images
        """
        images = set()
        for template in self.templates:
            template_images = list(collect_values_of_key_by_type(template, 'image', str))
            images.update(template_images)

            logging.debug('Images found in current template: %s', template_images)

        logging.debug('All found images: %s', images)
        return images

    def get_annotations_by_object_kind(self, kind):
        """Get annotations

        :param kind: Place to search from, defaults to "ConfigMap"
        :return: Annotations as dictionary
        """
        annotations = {}

        try:
            # Get the first template of the specified "kind"
            template = next(template for template in self.templates if template.get('kind') == kind)
            annotations = template.get('metadata', {}).get('annotations', {})
        except StopIteration:
            logging.warning('Annotations could not be found')

        return annotations

    @staticmethod
    def __load_into_yaml(helm_template):
        if isinstance(helm_template, bytes):
            decoded_template = helm_template.decode('utf-8')
        else:
            decoded_template = helm_template.replace('\t', ' ').rstrip()

        return yaml.load_all(decoded_template, Loader=yaml.SafeLoader)
