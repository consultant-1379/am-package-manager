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
"""Utilities"""
import os
import re
import shutil
import pathlib
import logging
import tarfile
import tempfile
import textwrap
import argparse
from contextlib import contextmanager
import yaml

from eric_am_package_manager.generator.cnf_values_file_exception import CnfValuesFileException

PATH_TO_LICENSES = 'Files/Licenses'


# pylint: disable=too-few-public-methods
class EnvDefault(argparse.Action):
    """
    Argparse action to get default value from environment variable
    """

    def __init__(self, variable, required=True, default=None, **kwargs):
        if not default and variable:
            if variable in os.environ:
                default = os.environ[variable]
        if required and default:
            required = False
        super().__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class CertificateInfo:
    """Simple object for storing attributes.

    Implements equality by attribute names and values, and provides a simple
    string representation.
    """

    def __init__(self, certificate, digest, privkey, manifest):
        self.certificate = certificate
        self.digest = digest
        self.privkey = privkey
        self.manifest = manifest

    def __eq__(self, other):
        if not isinstance(other, CertificateInfo):
            return NotImplemented
        return vars(self) == vars(other)

    def __contains__(self, key):
        return key in self.__dict__


def valid_file(fname):
    """
    Argparse argument type to verify that the argument is an existing file
    """
    fpath = os.path.realpath(fname)
    if os.path.isfile(fpath) and os.access(fpath, os.R_OK):
        return fname
    raise argparse.ArgumentTypeError(
        f'The value [{fname}] provided is not a valid file path, or it is not '
        'accessible for the user.')


def get_general_licenses_path(args):
    """
    Get License path, if not define returns empty
    """
    if args.license or args.licenses:
        return PATH_TO_LICENSES
    return ''


def valid_path(fname):
    """
    Argparse argument type to verify that the argument is a valid path
    """
    fpath = os.path.realpath(fname)
    if os.path.exists(fpath) and os.access(fpath, os.R_OK):
        return fname
    raise argparse.ArgumentTypeError(
        f'The value [{fname}] provided is not a valid path, or it '
        'is not accessible for the user.')


def valid_directory(fname):
    """
    Argparse argument type to verify that the argument is an existing directory
    """
    fpath = os.path.realpath(fname)
    if os.path.isdir(fpath) and os.access(fpath, os.R_OK | os.X_OK):
        return fname
    raise argparse.ArgumentTypeError(
        f'The value [{fname}] provided is not a valid directory path, or it '
        'is not accessible for the user.')


def strip_version(version):
    """Strip build ID from version

    >>> strip_version("1.1.11-EP1")
    '1.1.11-EP1'
    >>> strip_version("1.1.1-12")
    '1.1.1'
    >>> strip_version("1.1.11+12")
    '1.1.11'
    """
    return re.sub('([0-9]+.[0-9]+.[0-9]+)((?:[+-]EP[0-9]+)?).*', r'\1\2', version)


def collect_values_of_key_by_type(yaml_content, yaml_key, yaml_key_type):
    """
    Find key in dictionary

    :param yaml_content: Dictionary to search from
    :param yaml_key: Key to find
    :param yaml_key_type: Wanted type of the value
    :yield: Found keys
    """
    if hasattr(yaml_content, 'items'):
        for key, value in list(yaml_content.items()):
            if key == yaml_key and isinstance(value, yaml_key_type):
                yield value
            if isinstance(value, dict):
                for result in collect_values_of_key_by_type(value, yaml_key, yaml_key_type):
                    yield result
            elif isinstance(value, list):
                for item in value:
                    for result in collect_values_of_key_by_type(item, yaml_key, yaml_key_type):
                        yield result


@contextmanager
def extract(tar_file):
    """
    Extract Helm chart to temporary directory.
    :param tar_file to be extracted
    :return Temporary directory as context manager
    """
    temp_file = None
    try:
        temp_file = tempfile.mkdtemp()
        with tarfile.open(tar_file) as tar:
            tar.extractall(temp_file)
            yield os.path.join(temp_file, os.listdir(temp_file)[0])
    finally:
        if temp_file is not None:
            shutil.rmtree(temp_file)


def indent(text, bullet='-'):
    """
    Indents the given text

    :param text Text to be indentated
    :param bullet Optional character to be added on the beginning
    :return returns the indentated text
    """
    return bullet + textwrap.indent(text, '  ')[1:]


def load_yaml_file(filename):
    """Load YAML file as dictionary"""
    try:
        with open(filename, 'r', encoding='utf-8') as yaml_file:
            try:
                return yaml.safe_load(yaml_file)
            except yaml.YAMLError:
                logging.warning('File %s could not be loaded', filename)
    except IOError:
        logging.warning('File %s not available', filename)

    return {}


def is_cnf_yaml_file_correct(file_path):
    """Validate YAML by loading file as dictionary"""
    try:
        with open(file_path, 'r', encoding='utf-8') as yaml_file:
            filename = pathlib.Path(file_path).stem
            try:
                yaml.safe_load(yaml_file)
                return True
            except yaml.YAMLError as err:
                problem = getattr(err, 'problem', repr(err))
                logging.error('File %s could not be loaded: %s', filename, problem)
                raise CnfValuesFileException(
                    f'File {filename} could not be loaded: {problem}') from err
    except IOError as io_err:
        logging.error('File %s not available: %s ', file_path, str(io_err))
        raise FileNotFoundError(
            f'File {file_path} not available: {str(io_err)}') from io_err


def is_yaml_format_file(fpath):
    """Check file format"""
    if not (os.path.isfile(fpath) and os.path.getsize(fpath) > 0):
        raise CnfValuesFileException('Cnf values file is empty')
    return fpath.endswith('.yaml')


def is_chart_in_list_product_info_charts(args, chart):
    """Check do the chart is in the eric product info charts list"""
    product_info_chart_list = args.eric_product_info_charts
    return product_info_chart_list and os.path.basename(chart) in get_chart_base_names(
        product_info_chart_list)


def get_chart_base_names(product_info_charts):
    """Get base file name"""
    chart_names = set()
    for product_info_chart in product_info_charts:
        chart_names.add(os.path.basename(product_info_chart))
    return chart_names
