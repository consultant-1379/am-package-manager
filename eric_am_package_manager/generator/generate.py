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
'''Generate'''

import itertools
import pathlib
from functools import partial
import json
import logging
import os
import shutil
import sys
import tarfile
from itertools import filterfalse
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from subprocess import check_call, check_output, CalledProcessError
from tempfile import TemporaryDirectory
from glob import glob
from datetime import datetime
import re
# pylint: disable=import-error
import docker

from yaml import load, safe_load, dump
from . import utils
from .cnf_values_file_exception import CnfValuesFileException

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .helm_template import HelmTemplate
from .image import Image
from .utils import extract, PATH_TO_LICENSES
from .crd_handler import extract_crds
from .docker_api import DockerApi

_DOCKER_SAVE_FILENAME = 'docker.tar'
RELATIVE_PATH_TO_HELM_CHART = 'Definitions/OtherTemplates/'
RELATIVE_PATH_TO_FILES = 'Files/'

METADATA_KEYS_DEFAULT = {
    'vnf_provider_id',
    'vnf_product_name',
    'vnf_release_date_time',
    'vnf_package_version'}

METADATA_KEYS_FULL = {
    'vnfd_id',
    'vnf_provider_id',
    'vnf_product_name',
    'vnf_release_date_time',
    'vnf_package_version',
    'vnfm_info',
    'vnf_software_version',
    'compatible_specification_versions'}

VNFD_ID_METADATA_KEY = 'vnfd_id'


def __get_helm_executable(helm3, helm_version):
    if helm_version is None:
        return 'helm3' if helm3 else 'helm'
    return f'helm_{helm_version}'


def __build_helm_options(helm3, values, set_parameters, helm_debug, is_upgrade):
    helm_options = []
    helm_options.append("--debug" if helm_debug else "")
    helm_options.append("--is-upgrade" if is_upgrade else "")

    if values:
        helm_options.append(' --values ' + ','.join(values))

    if set_parameters:
        helm_options.append(' --set ' + ','.join(set_parameters))

    if not set_parameters and not values and not helm3:
        logging.warning("""This is adding '--set ingress.hostname=a' to the helm template command,
                           if you have not specified any set/values.
                           This is now deprecated and will be removed.
                           If you rely on it please update your execution of the tool to add this
                           set/value""")
        helm_options.append(' --set ingress.hostname=a')

    return ''.join(helm_options)


def __get_images(args):
    collected_images = []
    helm_template_images = None

    for archive_path in __get_archive_paths(args):
        if not args.helmfile and not args.disable_helm_template:
            helm_template_images = __get_helm_template_images(args, archive_path)

        if args.eric_product_info or utils.is_chart_in_list_product_info_charts(args, archive_path):
            product_info_info_images = \
                __get_product_info_images(args, archive_path, helm_template_images)
            collected_images.extend(product_info_info_images)

        elif not args.disable_helm_template:
            collected_images.extend(helm_template_images)

    return collected_images


def __get_product_info_images(args, archive, helm_template_images):
    """
    Get images from eric-product-info.yaml file
    :param args: Command line arguments
    :param helm_template_images: Set of helm template images
    :return: Set of images from charts eric-product-info.yaml
    """
    product_info_info_images = set()
    archive_without_product_info_yaml = []
    with extract(archive) as archive_directory:
        product_info_info_images.update(
            __get_images_from_eric_product_info(archive_directory,
                                                archive_without_product_info_yaml))

    __validate_images(args, archive_without_product_info_yaml,
                      helm_template_images, product_info_info_images)
    return product_info_info_images


def __validate_images(args, archive_without_product_info_yaml,
                      helm_template_images, product_info_info_images):
    """
    Validate matching of helm template and product info image sets
    :param args: Command line arguments
    :param archive_without_product_info_yaml:
        Array of archives that do not have product info yaml file
    :param helm_template_images: Set of helm template images
    :param product_info_info_images: Set images from eric-product-info.yaml file
    """
    if args.disable_helm_template:  # Using eric-product-info.yaml as only source
        if archive_without_product_info_yaml:
            logging.error("Helm charts not following DR-D1121-067, "
                          "missing eric-product-info.yaml: %s",
                          ", ".join(archive_without_product_info_yaml))
            sys.exit(1)

        __validate_images_exist_in_registry(args, product_info_info_images)
    else:
        if not args.helmfile:
            __validate_helm_template_images_match_product_info_images(
                helm_template_images, product_info_info_images)
        else:
            __validate_images_exist_in_registry(args, product_info_info_images)


def __get_helm_template_images(args, chart):
    """
    Get images from eric-product-info.yaml file
    :param args: Command line arguments
    :param chart: Helm chart
    :return: Set of images that found in result of command 'helm template' for chart
    """
    helm_command = __get_helm_executable(args.helm3, args.helm_version)
    helm_options = __build_helm_options(
        args.helm3, args.values, args.set, args.helm_debug, args.is_upgrade)
    helm_template_images = set()
    helm_template_output = __template_helm_chart(chart, helm_command, helm_options)
    helm_template_images.update(__parse_images_from_template(helm_template_output))
    if __images_in_scalar_values(helm_template_output):
        images_from_scalar_values = __handle_images_in_scalar_values(chart, args)
        if len(images_from_scalar_values) == 0:
            logging.warning(
                "Could not parse the image urls from the values.yaml file "
                "at root of chart. Please check the logs below to ensure all images "
                "have been packaged into the csar")

        helm_template_images.update(images_from_scalar_values)
    return helm_template_images


def __validate_images_exist_in_registry(args, product_info_info_images):
    docker_api = DockerApi(args.docker_config, args.timeout)
    product_info_info_images_as_str = map(str, product_info_info_images)

    image_not_found_in_registry = set(filterfalse(
        docker_api.image_exists, product_info_info_images_as_str))

    if len(image_not_found_in_registry) > 0:
        joined_images = '\n'.join(image_not_found_in_registry)
        logging.error('Images not found from the repository:\n%s', joined_images)
        sys.exit(1)


def __validate_helm_template_images_match_product_info_images(
        helm_template_images, product_info_info_images):
    not_in_helm_template = product_info_info_images.difference(helm_template_images)
    not_in_eric_product_info = helm_template_images.difference(product_info_info_images)

    if not_in_helm_template:
        logging.warning('Images not found from Helm template:\n%s',
                        '\n'.join(map(str, not_in_helm_template)))

    if not_in_eric_product_info:
        logging.error('Images not found from eric-product-info.yaml files:\n%s',
                      '\n'.join(map(str, not_in_eric_product_info)))
        sys.exit(1)


def __template_helm_chart(chart, helm_command, helm_options):
    command = f'{helm_command} template {helm_options} {chart}'

    logging.info('Executing helm template: %s', command)
    try:
        return check_output(command.split())
    except CalledProcessError:
        logging.exception('Helm template command failed for chart %s', chart)
        sys.exit(1)


def __get_images_from_eric_product_info(archive_directory, archive_without_eric_product_info):
    """Get images from a chart directory recursively

    :param archive_directory: Helm chart or Helmfile directory
    :param archive_without_eric_product_info: List of Helm charts with
                                              missing eric-product-info.yaml
    :return: List of images
    """
    images = []
    eric_product_info_file = os.path.join(archive_directory, 'eric-product-info.yaml')

    if os.path.isfile(eric_product_info_file):
        with open(eric_product_info_file, encoding='utf-8') as eric_product_info:
            data = safe_load(eric_product_info)
            images.extend(__parse_images_from_eric_product_info(data))
    else:
        logging.debug('Archive %s does not contain eric-product-info.yaml',
                      os.path.basename(archive_directory))
        archive_without_eric_product_info.append(os.path.basename(archive_directory))

    charts_directory_files = glob(os.path.join(archive_directory, 'charts/*'))
    sub_charts = (sub_chart for sub_chart in charts_directory_files if os.path.isdir(sub_chart))
    for sub_chart in sub_charts:
        images.extend(__get_images_from_eric_product_info(
            sub_chart, archive_without_eric_product_info))

    for crd_chart in glob(os.path.join(archive_directory, 'eric-crd/*.tgz')):
        with extract(crd_chart) as crd_directory:
            logging.debug('Found CRD Helm chart %s', os.path.basename(crd_chart))
            images.extend(__get_images_from_eric_product_info(
                crd_directory, archive_without_eric_product_info))

    logging.debug('Archive %s has %s images', os.path.basename(archive_directory), len(images))
    return images


def __parse_images_from_eric_product_info(eric_product_info):
    parsed_images = []
    if 'images' in eric_product_info:
        images = eric_product_info.get('images')

        # Detect malformed product_info files
        if not isinstance(images, dict):
            logging.warning('Malformed eric-product-info: images section must be a dict')
            return []

        for product_info in images.values():
            registry = product_info.get('registry')
            repo_path = product_info.get('repoPath')
            name = product_info.get('name')
            tag = product_info.get('tag')
            repo = f'{registry}/{repo_path}/{name}'
            image = Image(repo=repo, tag=tag)
            parsed_images.append(image)
    return parsed_images


def __images_in_scalar_values(helm_template_output):
    """
    This method gets the "image:" lines from the helm template output and checks to see
    if any line contains {{
    :param helm_template_output:
    :return: True if the image tags contain {{
    """
    if not isinstance(helm_template_output, str):
        helm_template_output = helm_template_output.decode()
    return bool([line for line in re.findall('.*image:.*', helm_template_output) if '{{' in line])


def __get_archive_paths(args):
    """Get Helm charts file paths from command line arguments

    :param args: Command line arguments
    :return: List of Helm charts
    """
    archive_paths = []
    if args.helm_dir:
        archive_paths.extend(glob(os.path.join(os.path.abspath(args.helm_dir), '*.tgz')))
    if args.helm:
        archive_paths.extend(args.helm)
    if args.helmfile:
        archive_paths.extend(args.helmfile)
    return archive_paths


def __handle_images_in_scalar_values(helm_chart, args):
    logging.info(
        'Helm template contains images in a scalar value, '
        'will parse the values file for the remaining images')
    if args.helm3:
        command = f'helm3 show values {helm_chart}'
        if args.helm_version is not None:
            command = f'helm_{args.helm_version} show values {helm_chart}'
    else:
        command = f'helm inspect values {helm_chart}'

    logging.info('Command is: %s', command)
    try:
        values = check_output(command.split())
    except CalledProcessError as exc:
        raise EnvironmentError(f'Helm command failed with error message: {str(exc)}') from exc

    return __parse_values_file_for_images(values)


def __parse_values_file_for_images(values_file_contents):
    """
    This method will parse a values file which follows the ADP Helm Chart
    Design Rules and Guidelines
    https://confluence.lmera.ericsson.se/pages/viewpage.action?spaceKey=AA&title=Helm+Chart+Design+Rules+and+Guidelines
    Specifically rules: DR-HC-050 and DR-HC-101
    The values file is from an integration helm chart to DR-HC-050 should be nested
    under the name of the child chart
    Here follows an example of a values file which will be parsed correctly:
    ```
        global:
          registry:
            url: armdocker.rnd.ericsson.se
            pullSecret: armdocker
        eric-mesh-sidecar-injector:
          imageCredentials:
            repoPath: proj-adp-gs-service-mesh
            pullPolicy: IfNotPresent
            registry:
              url:
              #pullSecret:

          images:
            sidecar_injector:
              name: eric-mesh-sidecar-injector
              tag: 1.1.0-130
            proxy:
              name: eric-mesh-proxy
              tag: 1.1.0-130
            proxy_init:
              name: eric-mesh-proxy-init
              tag: 1.1.0-130
        eric-mesh-controller:
          imageCredentials:
            repoPath: proj-adp-gs-service-mesh
            pullPolicy: IfNotPresent
            registry:
              url:
              #pullSecret:

          images:
            pilot:
              name: eric-mesh-controller
              tag: 1.1.0-130
            proxy:
              name: eric-mesh-proxy
              tag: 1.1.0-130
            kubectl:
              name: eric-mesh-tools
              tag: 1.1.0-130
    ```

    :param values_file_contents: the contents of the values file from the integration helm chart
    :return: a list of Images
    """
    data = load(values_file_contents, Loader=Loader)
    global_root = data.get('global')

    if global_root is None:
        logging.warning('Could not find global in the values.yaml file')
        return set()

    registry = global_root.get('registry')

    if registry is None:
        logging.warning('Could not find global.registry in the values.yaml file')
        return set()

    global_registry_url = registry.get('url')

    if global_registry_url is None:
        logging.warning('Could not find global.registry.url in the values.yaml file')
        return set()

    logging.info('Global registry url is: %s', global_registry_url)
    image_list = set()

    for key in list(data.keys()):
        if key != 'global':
            sub_chart = data.get(key)
            if isinstance(sub_chart, dict):
                image_credentials = sub_chart.get('imageCredentials')
                if image_credentials is None:
                    logging.warning('Could not find imageCredentials in %s', key)
                    continue
                repo_path = image_credentials.get('repoPath')
                if repo_path is None:
                    logging.warning('Could not find repoPath in %s', key)
                    continue
                logging.info('Repo path is: %s', repo_path)
                for sub_key in list(sub_chart.keys()):
                    __look_for_images(
                        global_registry_url, image_list, repo_path, sub_chart, sub_key)
            else:
                logging.warning('Could not find imageCredentials in %s', key)
    return image_list


def __look_for_images(global_registry_url, image_list, repo_path, sub_chart, sub_key):
    """
    This method will parse the images section of a values file which
    follows the ADP Helm Chart Design Rules and Guidelines
    https://confluence.lmera.ericsson.se/pages/viewpage.action?spaceKey=AA&title=Helm+Chart+Design+Rules+and+Guidelines
    Specifically rules: DR-HC-050
    Here follows an example of a values file images section which will be parsed correctly:
    ```
    images:
      sidecar_injector:
        name: eric-mesh-sidecar-injector
        tag: 1.1.0-130
      proxy:
        name: eric-mesh-proxy
        tag: 1.1.0-130
      proxy_init:
        name: eric-mesh-proxy-init
        tag: 1.1.0-130
    ```

    :param global_registry_url: the parsed global registry url to be used
    :param image_list: the list of images to populate
    :param repo_path: the parsed repo path to be used
    :param sub_chart: the parent section of the values file
    :param sub_key: the key of the parent section of the values file
    :return: a list of images
    """
    if sub_key == 'images':
        images = sub_chart.get(sub_key)
        for images_key in list(images.keys()):
            name = images.get(images_key).get('name')
            if name is None:
                logging.warning('Could not find name in %s', images_key)
                continue
            repo = f'{global_registry_url}/{repo_path}/{name}'
            tag = images.get(images_key).get('tag')
            if tag is None:
                logging.warning('Could not find tag in %s', images_key)
                continue
            image = Image(repo=repo, tag=tag)
            logging.info('Repo is: %s', str(image))
            image_list.add(image)


def __parse_images_from_template(helm_template):
    helm_template_images = HelmTemplate(helm_template).get_images()
    return __parse_images(helm_template_images)


def __parse_images(images):
    image_list = []
    for image in images:
        stripped = image.strip()
        if not stripped:
            continue
        split = stripped.split(':', 1)
        if len(split) > 1:
            parsed_image = Image(repo=split[0], tag=split[1])
        else:
            parsed_image = Image(repo=split[0])
        image_list.append(parsed_image)
        logging.info('Repo is: %s', parsed_image)
    return image_list


def __pull_images_with_docker(images, pull_timeout):
    logging.info('Pulling the images')
    pool = ThreadPool(cpu_count())
    pool.map(partial(__pull_image, pull_timeout=pull_timeout), images)
    pool.close()
    pool.join()
    logging.info('Images pulled')


def __pull_image(image, pull_timeout):
    client = docker.from_env(timeout=int(pull_timeout))
    logging.info('Pulling %s', image)
    client.images.pull(repository=image.repo, tag=image.tag)
    client.close()


def __save_images_to_tar(images, docker_save_filename):
    logging.info('Saving images to tar')

    list_of_images = ' '.join(map(str, images))

    logging.debug('List of images: %s', list_of_images)

    # docker api cannot be used as the save() method doesn't support multiple images.
    # https://github.com/docker/docker-py/issues/1149
    try:
        docker_save_command = f'docker save -o {docker_save_filename} {list_of_images}'
        output = check_output(docker_save_command.split())
    except CalledProcessError as exc:
        logging.error('Docker save command failed:\n%s', exc.stderr)
        sys.exit(1)

    logging.debug('Docker save output: %s', output)

    size = os.path.getsize(docker_save_filename)
    logging.debug('Docker save size %s bytes', size)


def __write_images_to_file(images_file_path, images):
    with open(images_file_path, 'w+', encoding='utf-8') as temp_images:
        image_names = list(map(str, images))
        dump({'images': [{'image': image} for image in image_names]}, temp_images)


def __pull_images_with_agentk(args, images_file_path, image_path):
    agentk_env = {'DOCKER_CONFIG': args.docker_config}
    agentk_command = [
        '/usr/bin/agent-k', 'export', '--no-scan-chart',
        '--input', images_file_path, '--output', image_path]

    if args.log == 'DEBUG':
        agentk_command.extend(['--debug'])

    logging.info('Fetching images with Agent-k')
    try:
        check_call(agentk_command, env=agentk_env)
    except CalledProcessError as exc:
        raise EnvironmentError('Agent-k command failed') from exc


def create_docker_tar(directory, args):
    """Create Docker tar

    :param directory: CSAR packaging directory
    :param args: Command line arguments
    :raises EnvironmentError: Error if packaging failed
    :return: Path to the generated Docker tar
    """
    logging.debug('Helm Arg archives: %s', args.helm)

    images = __get_images(args)
    image_path = os.path.join(directory, 'Files/images', _DOCKER_SAVE_FILENAME)

    if args.agentk:
        with TemporaryDirectory() as tempdir:
            images_file_path = os.path.join(tempdir, 'images.yaml')
            __write_images_to_file(images_file_path, images)
            __pull_images_with_agentk(args, images_file_path, image_path)
    else:
        __pull_images_with_docker(images, args.timeout)
        __save_images_to_tar(images, image_path)

    return image_path


def create_source(directory, args):
    """Add the source files to CSAR directory

    :param directory: CSAR packaging directory
    :param args: Command line arguments
    """
    logging.info('Adding files to source directory')
    definitions_path = os.path.join(directory, 'Definitions')
    chart_path = os.path.join(directory, 'Definitions/OtherTemplates/')
    scripts_path = os.path.join(directory, 'Scripts')
    licenses_path = os.path.join(directory, PATH_TO_LICENSES)
    images_path = os.path.join(directory, 'Files/images')

    os.makedirs(images_path, exist_ok=True)
    os.makedirs(definitions_path, exist_ok=True)
    os.makedirs(chart_path, exist_ok=True)

    add_definitions(args, definitions_path)

    if args.scripts:
        shutil.copytree(args.scripts, scripts_path)

    if args.licenses:
        shutil.copytree(args.licenses, licenses_path)

    if args.license:
        for license_file in args.license:
            shutil.copy(license_file, licenses_path)

    helm_chart_dict = {}
    add_helm(args, chart_path, helm_chart_dict)
    add_helmfile(args, chart_path, helm_chart_dict)

    add_helm_dir_to_chart_path(args, chart_path, helm_chart_dict)

    if args.extract_crds:
        charts = __get_archive_paths(args)
        for chart in charts:
            with extract(chart) as helmdir:
                extract_crds(pathlib.Path(helmdir),
                             pathlib.Path(chart_path))

    if args.scale_mapping is not None:
        os.link(os.path.abspath(args.scale_mapping),
                os.path.join(chart_path, os.path.basename(args.scale_mapping)))

    add_cnf_values_dir_to_chart_path(args, chart_path, helm_chart_dict)
    add_cnf_values_to_chart_path(args, chart_path, helm_chart_dict)


def add_helm(args, chart_path, helm_chart_dict):
    """Add Helm to chart path"""
    if args.helm:
        for helm in args.helm:
            set_helm_chart_path_to_dict(helm, helm_chart_dict)
            os.link(os.path.abspath(helm),
                    os.path.join(chart_path, os.path.basename(helm)))


def add_helmfile(args, chart_path, helmfile_archive_dict):
    """Add Helmfile to helmfile path"""
    if args.helmfile:
        for helmfile in args.helmfile:
            set_helm_chart_path_to_dict(helmfile, helmfile_archive_dict)
            os.link(os.path.abspath(helmfile),
                    os.path.join(chart_path, os.path.basename(helmfile)))


def add_definitions(args, definitions_path):
    """Add Definitions to chart path"""
    if args.definitions:
        if os.path.isdir(args.definitions):
            definition_files = [filename for filename in os.listdir(args.definitions) if
                                os.path.isfile(os.path.join(args.definitions, filename))]
            for definition_file in definition_files:
                shutil.copy(os.path.join(args.definitions, definition_file), definitions_path)
        else:
            shutil.copy(args.definitions, definitions_path)


def add_helm_dir_to_chart_path(args, chart_path, helm_chart_dict):
    """Add Helm path to chart path"""
    if args.helm_dir:
        for _, _, files in os.walk(args.helm_dir):
            for filepath in files:
                if '.tgz' in filepath:
                    set_helm_chart_path_to_dict(os.path.join(args.helm_dir, filepath),
                                                helm_chart_dict)
                    os.link(os.path.abspath(os.path.join(args.helm_dir, filepath)),
                            os.path.join(chart_path, filepath))


def add_cnf_values_dir_to_chart_path(args, chart_path, helm_chart_dict):
    """Add CNF values to chart path"""
    if args.values_cnf_dir and os.path.isdir(args.values_cnf_dir):
        files_cnf = get_values_cnf_dict(args)
        put_cnf_values_to_chart_path(chart_path, files_cnf, helm_chart_dict)


def add_cnf_values_to_chart_path(args, chart_path, helm_chart_dict):
    """Add CNF values to chart path"""
    values_cnf_dict = {}
    if args.values_cnf_file:
        for cnf_file in args.values_cnf_file:
            add_file_to_dictionary(cnf_file, values_cnf_dict, '')
        put_cnf_values_to_chart_path(chart_path, values_cnf_dict, helm_chart_dict)


def set_helm_chart_path_to_dict(helm, helm_chart_dict):
    """Set helm chart path to dictionary"""
    if '.tgz' in helm:
        helm_chart_dict[pathlib.Path(helm).stem] = helm


def put_cnf_values_to_chart_path(chart_path, files_cnf, helm_chart_dict):
    """Set CNF values.yaml file to chart directory"""
    for key in files_cnf:
        cnf_file = files_cnf.get(key)
        if utils.is_yaml_format_file(cnf_file) and utils.is_cnf_yaml_file_correct(cnf_file):
            if key not in helm_chart_dict:
                raise CnfValuesFileException(
                    f'There is not matching Helm chart for values file {key}')
            try:
                os.link(os.path.abspath(cnf_file),
                        os.path.join(chart_path, os.path.basename(cnf_file)))
            except FileExistsError as exc:
                problem = exc.strerror
                logging.error('Cannot add CNF values file %s to chart path due to: %s',
                              cnf_file, exc)
                raise CnfValuesFileException(
                    f'Cannot add CNF values file {key} to chart path due to: {str(problem)}'
                ) from exc


def get_values_cnf_dict(args):
    """Create dictionary of CNF values files."""
    values_cnf_dict = {}
    values_cnf_dir = args.values_cnf_dir
    for file in os.listdir(values_cnf_dir):
        add_file_to_dictionary(file, values_cnf_dict, values_cnf_dir)
    return values_cnf_dict


def add_file_to_dictionary(file, values_cnf_dict, values_cnf_dir):
    """Add CNF values file to dictionary."""
    absolute_file_path = os.path.join(values_cnf_dir, file)
    if os.path.isfile(absolute_file_path):
        filename = pathlib.Path(file).stem
        values_cnf_dict[filename] = absolute_file_path


def create_docker_tar_link(directory, docker_file):
    """Create symbolic link to docker tar in CSAR packaging directory

    :param directory: CSAR packaging directory
    :param docker_file: Docker tar filename
    :return: Absolute path to Docker tar in destination
    """
    docker_save_path = os.path.join(directory, 'Files/images', _DOCKER_SAVE_FILENAME)
    os.symlink(os.path.realpath(docker_file), docker_save_path)
    return docker_save_path


def create_images_section(directory, docker_file):
    """Create images section in CSAR packaging directory

    :param directory: CSAR packaging directory
    :param docker_file: Docker tar filename
    """
    __create_images_txt_file(directory, docker_file)


def empty_images_section(directory):
    """Create empty images section in CSAR packaging directory

    :param directory: CSAR packaging directory
    """
    with open(os.path.join(directory, 'Files/images.txt'), 'w', encoding='utf-8') as file:
        file.close()


def create_path(directory, arg_to_check, path_in_source):
    """Copy artifact to CSAR packaging directory

    :param directory: CSAR packaging directory
    :param arg_to_check: Artifact to copy
    :param path_in_source: Path in destination
    :return: Path in destination directory
    """
    if arg_to_check:
        shutil.copy(arg_to_check, os.path.join(directory, path_in_source))
        return os.path.join(path_in_source, os.path.basename(arg_to_check))
    return ''


def __create_images_txt_file(directory, docker_file):
    with tarfile.open(docker_file, encoding='utf-8') as tar:
        manifest = tar.extractfile('manifest.json')
        if manifest is None:
            raise FileNotFoundError('manifest.json')
        data = json.loads(manifest.read())
        images = itertools.chain.from_iterable([image['RepoTags'] for image in data])
    with open(os.path.join(directory, 'Files/images.txt'), 'w', encoding='utf-8') as entry1:
        entry1.write('\n'.join(images))


def get_vnfd(directory, args):
    """Populate VNFD definitions to CSAR directory

    :param directory: CSAR packaging directory
    :param args: Command line arguments
    :return: VNFd filename
    """
    if args.vnfd:
        logging.info('Copying VNFD %s to Definitions', args.vnfd)
        shutil.copy(args.vnfd, os.path.join(directory, 'Definitions'))
        vnfd_file_name = os.path.join('Definitions', os.path.basename(args.vnfd))
    else:
        logging.info('Creating placeholder VNFD')
        vnfd_file_name = 'Definitions/TOSCA.yaml'

        with open(os.path.join(directory, vnfd_file_name), 'w', encoding='utf-8') as entry:
            entry.write('template base file')

    return vnfd_file_name


def check_digest(args):
    """Check digest from command line arguments

    :param args: Command line arguments
    :return: Digest string
    """
    if args.sha512 and (args.manifest or args.values_csar):
        return 'SHA-512'
    return ''


def create_manifest_file(directory, args):
    """Create manifest file from given arguments"""
    with open(args.values_csar, encoding='utf-8') as source:
        values_csar_dict = safe_load(source)

    manifest_content = 'metadata:\n'
    for metadata_key in METADATA_KEYS_FULL:
        if metadata_key == 'vnf_release_date_time':
            manifest_content += f'{metadata_key}: {datetime.now().isoformat()}\n'
        elif metadata_key in values_csar_dict:
            manifest_content += f'{metadata_key}: {values_csar_dict[metadata_key]}\n'

    manifest_file_name = 'TOSCA.mf'
    if args.vnfd:
        vnfd_name = str(os.path.basename(args.vnfd)).rsplit('.', 1)[0]
        manifest_file_name = f'{vnfd_name}.mf'

    manifest_file_path = os.path.join(directory, manifest_file_name)
    with open(manifest_file_path, 'w', encoding='utf-8') as write_stream:
        write_stream.write(manifest_content)
    return manifest_file_name
