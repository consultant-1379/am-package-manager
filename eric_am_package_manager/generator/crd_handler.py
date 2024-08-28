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
'''CRD handler'''
import os
import shutil
import logging
import re
from pathlib import Path


COMPONENT_PATTERN = r'(.*)-([0-9]+.[0-9]+.[0-9]+(?:[+-][0-9]+)?)'
VERSION_PATTERN = r'[+-.]'


def parse_filename(file):
    """Parse version information from filename

    :param file: Path object for the file parse
    :return Tuple of component and version information

    >>> parse_filename(Path('asdf-asdf-1.1.0.tgz'))
    ('asdf-asdf', ['1', '1', '0'])
    >>> parse_filename(Path('asdf-asdf-1.2.3+1.tgz'))
    ('asdf-asdf', ['1', '2', '3', '1'])
    >>> parse_filename(Path('asdfasdfasdf'))
    (None, None)
    """
    match = re.match(COMPONENT_PATTERN, file.name)

    if not match:
        logging.warning('Could not parse component name and version from "%s"', file.name)
        return None, None

    component, versionstr = match.groups()
    version = re.split(VERSION_PATTERN, versionstr)

    return component, version


def copy_crd(filepath, destination):
    """Copy or replace file in destination directory leaving the newer version

    :param filepath: Path of the file to copy
    :param destination: Destination to copy to
    """
    component, version = parse_filename(filepath)

    if not component or not version:
        logging.warning("Failed to copy CRD '%s'", filepath.name)
        return

    existing = next(destination.glob(f"{component}*"), None)

    if not existing:
        shutil.copy2(filepath, destination)
        return

    oldcomponent, oldversion = parse_filename(existing)
    if oldversion >= version:
        logging.debug('Newer or equal version already exists for "%s"', oldcomponent)
        return

    logging.info('Replacing old version of "%s"', oldcomponent)
    os.unlink(existing)
    shutil.copy2(filepath, destination)


def extract_crds(helm_dir, destination):
    """Extract CRDs from Helm chart to given directory

    :param helm_dir: Path of the extracted Helm chart
    :param destination: Destination to copy to
    """
    crd_dir = Path(helm_dir, "eric-crd")
    charts_dir = Path(helm_dir, "charts")

    if crd_dir.is_dir():
        for crd in filter(Path.is_file, crd_dir.iterdir()):
            logging.info('Extracting CRD "%s" from chart "%s"',
                         crd.name,
                         helm_dir.name)
            copy_crd(crd, destination)

    if os.path.isdir(charts_dir):
        for helm in filter(Path.is_dir, charts_dir.iterdir()):
            extract_crds(Path(charts_dir, helm), destination)
