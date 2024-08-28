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
"""Helm chart classes for product report"""

import os
from subprocess import check_output, CalledProcessError
import logging

from .utils import strip_version, load_yaml_file, indent, extract
from .docker_api import DockerApi, DockerApiError
from .helm_template import HelmTemplate
from .hash_utils import sha256


class ProductInfo(dict):
    """Common class for Product Report elements"""

    @classmethod
    def to_yaml(cls, representer, data):
        """Class representer for YAML dump"""
        return representer.represent_dict(data)

    def __repr__(self):
        return '\n'.join([f'{k}: {v}' for k, v in self.items()])

    def get_symmetric_diff(self, other):
        """Get differences on two objects

        :param other: Another ProductInfo object to compare to
        :return: Differences as dictionary
        """
        diff = list(self.items() ^ other.items())
        half = len(diff) // 2
        return dict(diff[:half]), dict(diff[half:])

    def is_valid(self):
        """Check all values set

        :return: False if not all values are set, else True
        """
        if not all(list(self.values())):
            logging.debug('Validation failed for %s', self)
            return False

        return True


class HelmData(ProductInfo):
    """Class representing Helm YAML output"""

    def __init__(self, **kwargs):
        super().__init__()
        self.path = kwargs.get('path', '')
        self['product_number'] = kwargs.get('product_number', '')
        self['product_version'] = strip_version(kwargs.get(
            'product_version', ''))
        self['package'] = kwargs.get('package', '')
        self['chart_name'] = kwargs.get('chart_name', '')
        self['chart_version'] = kwargs.get('chart_version', '')
        self['sha256sum'] = kwargs.get('sha256sum', '')

    def __str__(self):
        chart_name = self['chart_name']
        chart_version = self['chart_version']
        return f'Helm Chart {chart_name} version {chart_version}'


class ImageData(ProductInfo):
    """Class representing Docker image YAML output"""

    def __init__(self, **kwargs):
        super().__init__()
        self.path = kwargs.get('path', '')
        self['product_number'] = kwargs.get('product_number', '')
        self['product_version'] = kwargs.get('product_version', '')
        self['image'] = kwargs.get('image', '')
        self['image_name'] = kwargs.get('image_name', '')
        self['image_tag'] = kwargs.get('image_tag', '')
        self['sha256sum'] = kwargs.get('sha256sum', '')

    @classmethod
    def get_image_url(cls, image_metadata):
        """Get image URL from YAML data

        :param image_metadata: Docker image metadata
        :return: Image URL
        """
        image_path = os.path.join(image_metadata.get('registry'),
                                  image_metadata.get('repoPath'),
                                  image_metadata.get('name'))
        image_tag = image_metadata.get('tag')
        return f'{image_path}:{image_tag}'

    @classmethod
    def from_product_info(cls, image_metadata, sha256sum):
        """Create Product object from eric-product-info YAML data

        :param image_metadata: Docker image metadata
        :param sha256sum: SHA256 sum of manifest
        :return: ImageData object
        """
        image_name = cls.get_image_url(image_metadata)
        product_number = image_metadata.get('productNumber', '').split('/')[0]
        product_number = product_number.replace(' ', '')
        image_tag = image_metadata.get('tag', '')

        return cls(product_number=product_number,
                   product_version=strip_version(image_tag),
                   image=image_name,
                   image_name=image_metadata.get('name', ''),
                   image_tag=image_tag,
                   sha256sum=sha256sum)

    @classmethod
    def from_labels(cls, image_name, labels, sha256sum):
        """Create Product object from Docker labels

        :param image_name: Name of the Docker image
        :param labels: Docker image labels dictionary
        :param sha256sum: SHA256 sum of manifest
        :return: ImageData object
        """
        product_number = labels.get('com.ericsson.product-number', '')
        product_number = product_number.replace(' ', '')
        product_revision = labels.get('org.opencontainers.image.version', '')

        image_path, image_tag = image_name.split(':')
        image_basename = os.path.basename(image_path)

        return cls(
            product_number=product_number,
            product_version=strip_version(product_revision or image_tag),
            image=image_name,
            image_name=image_basename,
            image_tag=image_tag,
            sha256sum=sha256sum)

    def __str__(self):
        image_name = self['image_name']
        image_tag = self['image_tag']
        return f'Image {image_name} version {image_tag}'


# pylint: disable=too-many-instance-attributes, too-many-arguments
class HelmChart:
    """Class representing Helm Chart"""

    def __init__(self,
                 helmdir,
                 path,
                 sha256sum=None,
                 include_helm=False):
        """Object initialization

        :param helmdir: Helm chart directory on disk
        :param path: Full logical path of the Helm chart including the chart name, e.g.
            helm-chart-1.0.0.tgz/charts/another-chart-1.0.0.tgz
        :param sha256sum: SHA256 sum of Helm chart
        :param include_helm: Include Helm chart to list of components, defaults to False
        """
        self.data = HelmData(path=path,
                             package=os.path.basename(path),
                             sha256sum=sha256sum)
        self.helmdir = helmdir
        self.include_helm = include_helm

        self.config = {
            'docker_config': '',
            'helm_command': 'helm3',
            'helm_options': '',
            'disable_helm_template': False
        }

        self.chart = None
        self.eric_product_info = None
        self.docker_api = None
        self.template = None
        self.images = []
        self.packages = []

        self.errors = []
        self.warnings = []

    def __str__(self):
        return str(self.data)

    def parse(self):
        """"Parse Helm chart"""
        self.docker_api = DockerApi(self.config['docker_config'])
        self._parse_helm_template()
        self._parse_chart_metadata()
        self._process_chart_metadata()
        self._add_chart_images()
        self._scan_crds()
        self._scan_dependencies()

    def set_config(self, **kwargs):
        """Set configuration values"""
        self.config['docker_config'] = kwargs.get('docker_config', self.config['docker_config'])
        self.config['helm_command'] = kwargs.get('helm_command', self.config['helm_command'])
        self.config['helm_options'] = kwargs.get('helm_options', self.config['helm_options'])
        self.config['disable_helm_template'] = kwargs.get(
            'disable_helm_template', self.config['disable_helm_template'])

    def get_components(self):
        """Return all Helm charts and Docker images

        :return: List of Helm charts and Docker images
        """
        packages = []

        if self.include_helm:
            packages.append(self.data)

        images = self.images

        for package in self.packages:
            subpackages, subimages = package.get_components()
            packages.extend(subpackages)
            images.extend(subimages)

        return packages, images

    def get_errors(self):
        """Get error messages

        :return: List of error messages
        """
        errors = {self.data.path: self.errors} if self.errors else {}

        for package in self.packages:
            errors.update(package.get_errors())

        return errors

    def get_warnings(self):
        """Get warning messages

        :return: List of warning messages
        """
        warnings = {self.data.path: self.warnings} if self.warnings else {}

        for package in self.packages:
            warnings.update(package.get_warnings())

        return warnings

    def _get_annotations(self):
        """Get annotations from Helm template

        :return: Helm template annotations
        """
        if self.config['disable_helm_template']:
            self.warnings.append('Cannot use use Chart annotations '
                                 'as an alternative source. '
                                 'Option --disable-helm-template '
                                 'enabled.')

        if self.template:
            return self.template.get_annotations_by_object_kind('ConfigMap')
        return {}

    def _get_images_from_helm_template(self):
        """Return list of images from Helm template

        :return: List of images gathered from Helm template
        """
        if self.config['disable_helm_template']:
            self.warnings.append('Cannot get Docker images from the '
                                 'Helm Template. Option '
                                 '--disable-helm-template enabled.')

            return []
        if self.template:
            return self.template.get_images()
        return []

    def _parse_helm_template(self):
        """Parse Helm template YAML"""
        if self.config['disable_helm_template']:
            self.template = None
            return

        try:
            helm_command = self.config['helm_command']
            helm_options = self.config['helm_options']
            helm_output = check_output(
                f'{helm_command} template {helm_options} {self.helmdir}'.split())
            self.template = HelmTemplate(helm_output)
        except CalledProcessError:
            self.errors.append(f'Cannot get Helm template for: {self.data.path}')
            self.template = None

    def _parse_chart_metadata(self):
        """Parse Helm chart metadata as dictionary"""
        self.eric_product_info = load_yaml_file(
            f'{self.helmdir}/eric-product-info.yaml')
        self.chart = load_yaml_file(f'{self.helmdir}/Chart.yaml')

    def _process_chart_metadata(self):
        """Extract Product information from Helm chart"""
        self.data['chart_name'] = self.chart.get('name', '')
        self.data['chart_version'] = self.chart.get('version', '')

        if not self.eric_product_info:
            self.warnings.append('Helm Chart not conforming to '
                                 'DR-D1121-067, no eric-product-info.yaml')

        # Chart not included in the report. Not necessary to parse all data.
        if not self.include_helm:
            return

        product_number = self.eric_product_info.get('productNumber', '')
        product_version = strip_version(self.chart.get('version', ''))

        if not product_version:
            annotations = self._get_annotations()
            product_version = annotations.get('ericsson.com/product-revision',
                                              '')

        self.data['product_number'] = product_number.replace(' ', '')
        self.data['product_version'] = product_version

        if not self.data.is_valid() and self.include_helm:
            self.errors.append(f'Chart metadata not valid on:\n'
                               f'{indent(repr(self.data))}')

        logging.debug('%s added', self.data)

    def _scan_crds(self):
        """Add dependent CRD packages"""
        crd_dir = os.path.join(self.helmdir, 'eric-crd')

        if not os.path.isdir(crd_dir):
            logging.debug('No CRD packages in %s', self)
            return

        for crd_package in sorted(os.listdir(crd_dir)):
            helm_sha256 = sha256(os.path.join(crd_dir, crd_package))

            with extract(os.path.join(crd_dir, crd_package)) as helm:
                crd = HelmChart(helm,
                                f'{self.data.path}/eric-crd/{crd_package}',
                                helm_sha256,
                                include_helm=True)
                crd.set_config(**self.config)
                crd.parse()
                self.packages.append(crd)
                logging.info('Found CRD %s from %s, sha256: %s', crd, self, helm_sha256)

    def _scan_dependencies(self):
        """Add dependent Helm charts"""
        charts_dir = os.path.join(self.helmdir, 'charts')

        if not os.path.isdir(charts_dir):
            logging.debug('No charts dir in %s', self)
            return

        for dependency in sorted(os.listdir(charts_dir)):
            chart_path = os.path.join(charts_dir, dependency)
            helm = HelmChart(chart_path,
                             f'{self.data.path}/charts/{dependency}',
                             include_helm=False)
            helm.set_config(**self.config)
            helm.parse()
            self.packages.append(helm)
            logging.debug('Found dependency %s from %s', helm, self)

    def _add_image(self, image_metadata):
        """Add an image to images list

        :param image_metadata: ImageData object
        """
        image_metadata.path = self.data.path

        if not image_metadata.is_valid():
            self.errors.append(f'Image metadata not valid on:\n'
                               f'{indent(repr(image_metadata))}')

        self.images.append(image_metadata)
        logging.debug('%s added from %s', image_metadata, self.data)

    def _add_images_from_eric_product_info(self):
        """Add images from eric-product-info
        """
        for _, image_metadata in self.eric_product_info.get('images', {}).items():
            image_url = ImageData.get_image_url(image_metadata)

            try:
                sha256sum = self.docker_api.get_manifest_hash(image_url)
                eric_info_data = ImageData.from_product_info(image_metadata, sha256sum)
                labels = self.docker_api.get_labels(image_url)
                labels_data = ImageData.from_labels(image_url, labels, sha256sum)
            except DockerApiError as exc:
                self.errors.append(str(exc))
                continue

            if labels_data and labels_data != eric_info_data:
                diff = eric_info_data.get_symmetric_diff(labels_data)
                label_string = indent(f'Labels: {str(diff[1])}')
                chart_string = indent(f'Chart: {str(diff[0])}')
                self.errors.append(
                    f'Image labels not matching to '
                    f'product info in {image_url}:\n'
                    f'{label_string}\n'
                    f'{chart_string}')

            # Add image labels data if product info not valid
            if not eric_info_data.is_valid() and \
                    labels_data and labels_data.is_valid():
                self.warnings.append(f'eric_product_info.yaml not '
                                     f'valid on {labels_data}. '
                                     f'Using image labels as source.\n'
                                     f'{indent(repr(eric_info_data))}')
                self._add_image(labels_data)
            else:
                self._add_image(eric_info_data)

    def _add_images_from_helm_template(self):
        """Add images from Helm template
        """
        images = self._get_images_from_helm_template()

        for image_url in images:
            try:
                labels = self.docker_api.get_labels(image_url)
                sha256sum = self.docker_api.get_manifest_hash(image_url)
                labels_data = ImageData.from_labels(image_url, labels, sha256sum)
                self._add_image(labels_data)
            except DockerApiError as exc:
                self.errors.append(f'Could not add {image_url}: {str(exc)}')

    def _add_chart_images(self):
        """Add dependent Docker images to chart data"""
        if self.eric_product_info:  # get images through eric_product_info.yaml
            self._add_images_from_eric_product_info()
        else:  # Get images through Helm template
            self._add_images_from_helm_template()
