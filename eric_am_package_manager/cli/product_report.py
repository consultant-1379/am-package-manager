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
"""product Report"""

import sys
import argparse
import logging

from eric_am_package_manager.generator.product_report import helm_product_report, \
    csar_product_report, \
    ProductReportError
from eric_am_package_manager.generator.utils import valid_file
from .__main__ import SUPPORTED_HELM3_VERSIONS

DEFAULT_LOG_FORMAT = '[%(levelname)s] %(message)s'

logging.basicConfig(format=DEFAULT_LOG_FORMAT,
                    level=logging.INFO)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='product-report',
        add_help=False)

    common_parser = argparse.ArgumentParser(add_help=False)

    common_parser.add_argument(
        '--loglevel',
        default='info',
        help='Logging level',
        dest='loglevel'
    )
    common_parser.add_argument(
        '--product-report',
        help='Product report output file',
        default='out.yaml'
    )
    common_parser.add_argument(
        '--helm-debug',
        action='store_true',
        help='Run helm commands with debug option'
    )
    common_parser.add_argument(
        '--values',
        help='Values file for Helm commands',
        required=False
    )
    common_parser.add_argument(
        '--docker-config',
        help='''Path to Docker configuration''',
        default='/root/.docker'
    )
    common_parser.add_argument(
        '--helm3',
        action='store_true',
        help='To generate CSAR with Helm 3'
    )
    common_parser.add_argument(
        '--helm-version',
        help='Helm3 version to use',
        choices=SUPPORTED_HELM3_VERSIONS
    )
    common_parser.add_argument(
        '--disable-helm-template',
        action='store_true',
        help='''Disable parsing Helm template for dependencies in case
                DR-D1121-067 (eric_product_info.yaml) is not supported''',
        required=False
    )
    subparsers = parser.add_subparsers(
        description='Parse product report from a Helm chart',
        dest='command'
    )
    helm_parser = subparsers.add_parser(
        'helm',
        parents=[common_parser],
        help='Process Product Report from Helm chart'
    )
    helm_parser.add_argument(
        '--helm-chart-file',
        help='Helm chart file',
        nargs='+',
        type=valid_file,
        required=True
    )
    helm_parser.set_defaults(func=helm_product_report,
                             no_images=True)

    csar_parser = subparsers.add_parser(
        'csar',
        parents=[common_parser],
        help='Process Product Report from CSAR file'
    )
    csar_parser.add_argument(
        '--csar-file',
        help='CSAR file',
        type=valid_file,
        required=True
    )
    csar_parser.add_argument(
        '--no-compare-images',
        help='Do not compare the product report against Docker images list',
        action='store_true'
    )
    csar_parser.add_argument(
        '--no-compare-host',
        help='Compare only the image name and tag on Docker images list',
        action='store_true'
    )
    csar_parser.set_defaults(func=csar_product_report,
                             no_images=False)

    args = parser.parse_args()

    if not hasattr(args, 'func'):
        logging.error('Please provide a valid command')
        parser.print_help()
        sys.exit(1)

    logging.getLogger().setLevel(logging.getLevelName(args.loglevel.upper()))

    try:
        args.func(args)
    except ProductReportError as exc:
        logging.error('Failed to create product report: %s', exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
