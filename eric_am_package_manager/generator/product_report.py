#!/usr/bin/env python3
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
"""Product report"""

import logging
import os
import re
from zipfile import ZipFile, BadZipFile, LargeZipFile
import tempfile

from ruamel.yaml import YAML

# pylint: disable=import-error

from .utils import extract, indent, load_yaml_file
from .helm_utils import ImageData, HelmData, HelmChart
from .hash_utils import sha256

logging.getLogger('urllib3').setLevel(logging.WARNING)


class ProductReportError(Exception):
    """Error in Product Report generation"""


def yaml_dump(data, stream=None):
    """
    Dump OrderedDict as YAML.
    By default, pyyaml does is not aware of that type.

    :param data: Data to write
    :param stream: Stream to write to, defaults to None
    """
    yaml_item = YAML(typ='safe', pure=True)
    yaml_item.default_flow_style = False

    def _dict_representer(dumper, data):

        return dumper.represent_mapping(
            yaml_item.Resolver().DEFAULT_MAPPING_TAG,
            list(data.items()))

    yaml_item.Representer.add_representer(ImageData, _dict_representer)
    yaml_item.Representer.add_representer(HelmData, _dict_representer)
    return yaml_item.dump(data, stream)


def remove_duplicates(components, archive_type):
    """Remove duplicate components from final output

    :param components: Components dictionary from product report
    :param archive_type: Archive type - Helm or Helmfile
    """
    packages = {}
    images = {}

    for image in components['images']:
        existing = images.get(image['sha256sum'], {})
        if existing:
            logging.debug('Removing duplicate image %s', image)
            continue

        images[image['sha256sum']] = image

    for package in components['packages']:
        existing = packages.get(package['sha256sum'], {})
        if existing:
            logging.debug('Removing duplicate package %s', package)
            continue
        if archive_type == "helmfile":
            packages[package['helmfile_name']] = package
        else:
            packages[package['chart_name']] = package

    components['images'] = list(images.values())
    components['packages'] = list(packages.values())


def verify_all_components_valid(components):
    """Verify all components have valid data

    :param components: Components dictionary from product report
    :return: False if not all components have valid data
    """
    all_components = components['images'] + components['packages']
    invalid = [c for c in all_components if not c.is_valid()]

    if invalid:
        incomplete = [f'{c.path}:\n{indent(repr(c))}' for c in invalid]
        logging.error('Incomplete entries in the output file:\n%s\n',
                      '\n'.join(list(map(indent, incomplete))))
        return False

    return True


def verify_unique_product_numbers(components, archive_type):
    """Check that product numbers in product report are unique

    :param components: Components dictionary from product report
    :param archive_type: Archive type helm or helmfile
    :return: False if not all product numbers are unique
    """
    valid = True
    product_numbers = {}

    for component in components['images'] + components['packages']:
        product_number = component['product_number']
        product_numbers.setdefault(product_number, []).append(component)

    all_duplicates = {num: items for (num, items) in product_numbers.items()
                      if (len(items) > 1 and num)}

    def get_name(product):
        if archive_type == "helmfile":
            return product.get('image_name') or product.get('helmfile_name')
        return product.get('image_name') or product.get('chart_name')

    for product_number, products in all_duplicates.items():
        product_names = [get_name(p) for p in products]

        if len(products) != product_names.count(product_names[0]):
            duplicates = [f'{c.path}:\n{indent(repr(c))}' for c in products]
            logging.error('Same product number %s used in '
                          'multipe components:\n%s\n',
                          product_number,
                          '\n'.join(map(indent, duplicates)))
            valid = False

    return valid


def verify_all_images_in_report(args, images):
    """Verify contents of product report matches with the downloaded images

    :param args: Command line arguments
    :param images: List of images in product report
    :return: False if product report images do not match to downloaded
    """
    if args.no_images:
        logging.debug('Skipping image list validation')
        return True

    try:
        with ZipFile(args.name + '.csar', 'r') as csar:
            csar_images = csar.read('Files/images.txt').decode('utf-8')
    except (OSError, BadZipFile, LargeZipFile) as exc:
        logging.error('Failed to extract images.txt from CSAR: %s', exc)
        return False

    downloaded = set(csar_images.splitlines())
    report = {i['image'] for i in images}

    report_missing = downloaded - report
    download_missing = report - downloaded

    if report_missing or download_missing:
        if report_missing:
            logging.error('Images not in Product Report:\n%s\n',
                          '\n'.join(map(indent, report_missing)))
        if download_missing:
            logging.error('Images not in CSAR package:\n%s\n',
                          '\n'.join(map(indent, download_missing)))
        return False

    return True


def verify_unique_images(images):
    """Check images are unique for each product number

    :param args: CLI arguments
    :param images: List of images
    :return: False if errors found, else True
    """
    product_numbers = {}
    return_value = True

    for image in images:
        product = product_numbers.setdefault(image['product_number'], {})
        product.setdefault(image['product_version'], []).append(image)

    for product, versions in product_numbers.items():
        for version, components in versions.items():
            if len(components) > 1:
                return_value = False
                logging.error('Multiple images with same product number %s, version %s:\n%s',
                              product,
                              version,
                              '\n'.join([f'{indent(c.path + os.linesep + indent(repr(c)))}'
                                         for c in components]))
    return return_value


def check_for_errors(errors):
    """Check error messages from product report creation

    :param errors: Errors dictionary
    :return: False if errors found, else True
    """
    if errors:
        message = ''
        for path, error in errors.items():
            errors_str = '\n'.join(map(indent, error))
            message += f'{path}:\n{errors_str}\n'
        logging.error('Errors while processing product report:\n%s', message)
        return False
    return True


def check_for_warnings(warnings):
    """Check warning messages from product report creation

    :param warnings: Warnings dictionary
    """
    if warnings:
        message = ''
        for path, warn in warnings.items():
            warnings_str = '\n'.join(map(indent, warn))
            message += f'{path}:\n{warnings_str}\n'
        logging.warning('Warnings while processing product report:\n%s',
                        message)


def create_product_report(args, helms):
    """Create product report YAML file

    :param args: Command line arguments
    :param helms: List of Helm files
    :raises ProductReportError: Error in product report validation
    """
    output = {
        'includes': {
            'images': [],
            'packages': []
        }
    }
    errors = {}
    warnings = {}
    helm_command = 'helm3' if args.helm3 else 'helm'
    helm_options = ''

    if args.helm_version:
        helm_command = f'helm_{args.helm_version}'

    if args.values:
        joined_values = ','.join(args.values)
        helm_options += f' --values {joined_values}'

    if args.helm_debug:
        helm_options += ' --debug'

    for helm in helms:
        helm_sha256 = sha256(helm)

        logging.info('Processing Helm chart %s, sha256: %s',
                     os.path.basename(helm),
                     helm_sha256)

        with extract(helm) as helmdir:
            helm = HelmChart(helmdir, os.path.basename(helm),
                             helm_sha256, include_helm=True)
            helm.set_config(docker_config=args.docker_config,
                            helm_command=helm_command,
                            helm_options=helm_options,
                            disable_helm_template=args.disable_helm_template)
            helm.parse()
            packages, images = helm.get_components()
            output['includes']['packages'].extend(packages)
            output['includes']['images'].extend(images)

            errors.update(helm.get_errors())
            warnings.update(helm.get_warnings())

    remove_duplicates(output['includes'], archive_type="helm")

    try:
        with open(args.product_report, 'w', encoding='utf-8') as outfile:
            yaml_dump(output, outfile)

        logging.info('Wrote product report YAML file to %s',
                     args.product_report)
    except IOError as exc:
        raise ProductReportError(f'Failed to write product report'
                                 f'file to {args.product_report}') from exc

    check_for_warnings(warnings)

    if any((not check_for_errors(errors),
            not verify_unique_product_numbers(output['includes'], archive_type="helm"),
            not verify_all_components_valid(output['includes']),
            not verify_all_images_in_report(args,
                                            output['includes']['images']),
            not verify_unique_images(output['includes']['images']))):
        raise ProductReportError('Product report validation failed')


def get_helmfile_package_info(helmfile_metadata, helmfile_sha256):
    """Creates helmfile package info
        :param helmfile: helmfile name
        :param helmfile_metadata: helmfile metadata
        :param helmfile_sha256: sha256 code for helmfile
    """
    try:
        package_dict = {}
        packages = [package_dict]
        if not helmfile_metadata["name"] or not helmfile_metadata["version"]:
            raise ProductReportError('Helmfile metadata.yaml does not contain name and version.')
        package_dict["product_number"] = "TBC"
        package_dict["product_version"] = helmfile_metadata["version"]
        package_dict["package"] = f'{helmfile_metadata["name"]}-{helmfile_metadata["version"]}.tgz'
        package_dict["helmfile_name"] = helmfile_metadata["name"]
        package_dict["helmfile_version"] = helmfile_metadata["version"]
        package_dict["sha256sum"] = helmfile_sha256
    except Exception as exc:
        raise ProductReportError('Failed to write product report, something wrong with helmfile '
                                 'metadata.yaml .') from exc
    return packages


def create_helmfile_product_report(args, helmfiles):
    """Create product report YAML file

        :param args: Command line arguments
        :param helmfiles: List of Helmfiles
        :raises ProductReportError: Error in product report validation
        """
    output = {
        'includes': {
            'images': [],
            'packages': []
        }
    }
    errors = {}
    warnings = {}
    helm_command = 'helm3' if args.helm3 else 'helm'
    helm_options = ''

    for helmfile in helmfiles:
        helmfile_sha256 = sha256(helmfile)

        logging.info('Processing Helmfile %s, sha256: %s',
                     os.path.basename(helmfile),
                     helmfile_sha256)

        with extract(helmfile) as helmfiledir:
            helmfile_images = HelmChart(helmfiledir, os.path.basename(helmfile),
                                        helmfile_sha256, include_helm=False)
            helmfile_images.set_config(docker_config=args.docker_config,
                                       helm_command=helm_command,
                                       helm_options=helm_options,
                                       disable_helm_template=True)
            helmfile_images.parse()
            packages, images = helmfile_images.get_components()
            packages = get_helmfile_package_info(load_yaml_file(f'{helmfiledir}/metadata.yaml'),
                                                 helmfile_sha256)
            output['includes']['packages'].extend(packages)
            output['includes']['images'].extend(images)

            errors.update(helmfile_images.get_errors())
            warnings.update(helmfile_images.get_warnings())

    remove_duplicates(output['includes'], archive_type="helmfile")

    try:
        with open(args.product_report, 'w', encoding='utf-8') as outfile:
            yaml_dump(output, outfile)

        logging.info('Wrote product report YAML file to %s',
                     args.product_report)
    except IOError as exc:
        raise ProductReportError(f'Failed to write product report'
                                 f'file to {args.product_report}') from exc


def helm_product_report(args):
    """Create product report from Helm

    :param args: Command line arguments
    """
    create_product_report(args, args.helm_chart_file)


def csar_product_report(args):
    """Create product report from CSAR

    :param args: Command line arguments
    """
    with tempfile.TemporaryDirectory() as tempdir:
        with ZipFile(args.name + '.csar') as csar:
            tgz_pattern = re.compile('Definitions/OtherTemplates/.*tgz')
            archives = list(filter(tgz_pattern.match, csar.namelist()))
            csar.extractall(tempdir, archives)
            if args.helmfile:
                logging.info("Started Helmfile product report.")
                create_helmfile_product_report(args,
                                               [os.path.join(tempdir, h) for h in archives])
            if args.helm:
                logging.info("Started Helm Chart product report.")
                create_product_report(args,
                                      [os.path.join(tempdir, h) for h in archives])
