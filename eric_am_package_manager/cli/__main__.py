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
'''am-package-manager'''
import os
import sys
import zipfile
import argparse
import logging
import pathlib
import tarfile
from tempfile import TemporaryDirectory

from yaml import safe_load, dump, YAMLError

from vnfsdk_pkgtools.packager import utils as packager_utils, csar

from eric_am_package_manager.generator import generate, product_report, hash_utils, utils
from eric_am_package_manager.generator.utils import CertificateInfo, get_general_licenses_path

SIGNATURE_FILE_NAME = 'signature.csm'
SUPPORTED_HELM3_VERSIONS = ['3.4.2', '3.5.1', '3.6.3', '3.7.1', '3.8.1',
                            '3.8.2', '3.10.1', '3.10.3', '3.11.3',
                            '3.12.0', '3.13.0']


def __check_arguments(parser, args):
    """Check arguments
    """
    __check_helm_arguments(parser, args)
    __check_helmfile_arguments(parser, args)
    if args.values_csar:
        __check_values_csar_validity(parser, args.values_csar)

    if args.manifest and args.vnfd:
        manifest_name = os.path.basename(str(args.manifest)).rsplit('.', 1)[0]
        vnfd_name = os.path.basename(str(args.vnfd)).rsplit('.', 1)[0]
        if manifest_name != vnfd_name:
            parser.error('The name of both VNFD yaml file and manifest file must match.')
    check_pkg_option_arguments(args, parser)


def check_pkg_option_arguments(args, parser):
    """Check package option arguments
    """
    if (args.pkgOption == '1') and args.certificate and not args.manifest and not args.values_csar:
        parser.error('A valid manifest file must be provided if certificate is provided.')
    if (args.pkgOption == '2') and (not args.certificate or not args.key):
        parser.error('A valid certificate and key is not provided for Option 2')
    if (args.pkgOption == '2') and args.certificate:
        cert_name = os.path.basename(str(args.certificate)).rsplit('.', 1)[0]
        if cert_name != args.name:
            parser.error('Certificate name and csar name must match for Option 2.')
    if args.pkgOption in ('2', '1') and args.certificate:
        _, cert_extension = os.path.splitext(str(args.certificate))
        if cert_extension != '.cert':
            parser.error('Certificate extension must be \'.cert\'.')


def __check_helm_arguments(parser, args):
    if (args.helm or args.helm_dir) and args.helmfile:
        parser.error('Cannot use --helm/--helm_dir and --helmfile together')

    if not args.helmfile:
        if not args.helm and not args.helm_dir:
            parser.error('--helm or --helm-dir is required')

        if args.helm_dir:
            helm_charts_exist = False
            for _, _, files in os.walk(args.helm_dir):
                for filename in files:
                    if '.tgz' in filename:
                        helm_charts_exist = True
            if not helm_charts_exist:
                parser.error('The specified directory does not contain any helm charts')


def __check_helmfile_arguments(parser, args):
    if args.helmfile and len(args.helmfile) > 1:
        parser.error("More than 1 helmfile archives are not allowed")

    if args.helmfile and not is_valid_helmfile(args):
        parser.error("Provided helmfile archive is not a valid helmfile.")


def is_valid_helmfile(args):
    """Check if archive is a valid helmfile tgz."""
    tgz_filename = pathlib.Path(args.helmfile[0])
    with tarfile.open(tgz_filename, 'r:gz') as tgz:
        for member in tgz.getmembers():
            if member.isfile() and member.name.endswith('.yaml'):
                if member.name.split("/")[-1] == 'helmfile.yaml':
                    return True
        return False


def __check_values_csar_validity(parser, values_file):
    with open(values_file, encoding='utf-8') as source:
        values_csar_dict = safe_load(source)
        for key in generate.METADATA_KEYS_DEFAULT:
            if key != 'vnf_release_date_time' and key not in values_csar_dict:
                parser.error('The specified values-csar yaml file '
                             'does not contain all the required keys')
        for key in generate.METADATA_KEYS_FULL:
            if key != 'vnf_release_date_time' and key not in values_csar_dict:
                logging.warning("The specified values-csar yaml file does not contain key %s", key)
                logging.warning("This key %s is required starting from SOL 2.7.1", key)


def create_filename(args):
    """Generate csar file name
    :param args: Command line arguments
    """
    filename = f'{args.name}.csar'
    if os.path.exists(filename):
        logging.info('Deleting pre-existing csar file with the name: %s', filename)
        os.remove(filename)
    return filename


def generate_certificate_data(args, directory, path_to_manifest_in_source):
    """Generate CertificateInfo object
    :param args: Command line arguments
    :param directory: CSAR packaging directory
    :param path_to_manifest_in_source: Path to manifest
    """
    digest_value = generate.check_digest(args)
    path_to_cert_in_source = generate.create_path(
        directory, args.certificate, generate.RELATIVE_PATH_TO_FILES)
    return CertificateInfo(certificate=path_to_cert_in_source,
                           digest=digest_value,
                           privkey=args.key,
                           manifest=path_to_manifest_in_source)


def generate_csar_args(directory, args, filename, option_certificate_info):
    """Generate CSAR ARGs
    :param directory: CSAR packaging directory
    :param args: Command line arguments
    :param filename: name of CSAR package
    :param option_certificate_info: CertificateInfo object
    """
    path_to_helm_in_source = generate.RELATIVE_PATH_TO_HELM_CHART
    path_to_history_in_source = generate.create_path(
        directory, args.history, generate.RELATIVE_PATH_TO_FILES)

    return argparse.Namespace(helm=path_to_helm_in_source,
                              csar_name=filename,
                              history=path_to_history_in_source,
                              tests='',
                              licenses=get_general_licenses_path(args),
                              debug='',
                              created_by='Ericsson',
                              certificate=option_certificate_info.certificate,
                              digest=option_certificate_info.digest,
                              privkey=option_certificate_info.privkey,
                              manifest=option_certificate_info.manifest,
                              sol_version=args.sol_version
                              )


def generate_option1(directory, args, vnfd):
    """Generate command for pkgOption 1

    :param directory: CSAR packaging directory
    :param args: Command line arguments
    :param vnfd: VNFD definitions file
    :raises ValueError: Error in command execution
    """
    path_to_manifest_in_source = get_path_to_manifest(args, directory)
    filename = create_filename(args)

    certificate_data = generate_certificate_data(args, directory, path_to_manifest_in_source)

    csar_args = generate_csar_args(directory, args, filename, certificate_data)

    logging.debug('Csar args Option 1 %s', str(csar_args))

    csar.write(directory, vnfd, filename, csar_args)


def get_path_to_manifest(args, directory):
    """Generate path for manifest
    :param args: Command line arguments
    :param directory: package directory
    """
    if args.values_csar:
        path_to_manifest_in_source = generate.create_manifest_file(directory, args)
    else:
        path_to_manifest_in_source = generate.create_path(directory, args.manifest, '')
    return path_to_manifest_in_source


def generate_option2(directory, args, vnfd):
    """Generate command for pkgOption 2

    :param directory: CSAR packaging directory
    :param args: Command line arguments
    :param vnfd: VNFD definitions file
    :raises ValueError: Error in command execution
    """
    filename = create_filename(args)
    digest_value = generate.check_digest(args)
    certificate_data = CertificateInfo(certificate='',
                                       digest=digest_value,
                                       privkey='',
                                       manifest=get_path_to_manifest(args, directory))
    csar_args = generate_csar_args(directory, args, filename, certificate_data)

    logging.info('Csar args Option 2: %s', str(csar_args))

    csar.write(directory, vnfd, filename, csar_args)

    write_signature_for_option2(args, filename)


def write_signature_for_option2(args, filename):
    """Write Signature to CSAR package with Option 2
    :param args: Command line arguments
    :param filename: name of CSAR package
    """
    filename_full_path = os.path.abspath(filename)
    logging.debug('calculate signature: %s', args.certificate)
    signature = packager_utils.sign(msg_file=filename_full_path,
                                    cert_file=os.path.abspath(args.certificate),
                                    key_file=args.key)
    signature_name = os.path.basename(str(args.certificate)).rsplit('.', 1)[0] + '.cms'
    with open(signature_name, 'w', encoding='utf-8') as file:
        file.write(signature)
    destination = f'{args.name}.zip'
    if os.path.isfile(destination):
        logging.info('Deleting pre-existing csar file with the name: %s', destination)
        os.remove(destination)
    logging.debug('Compressing to make Option 2 csar')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as file:
        cert_file_full_path = os.path.abspath(args.certificate)

        logging.debug('Writing to archive: %s', cert_file_full_path)

        file.write(cert_file_full_path, os.path.basename(args.certificate))
        if os.path.isfile(signature_name):
            signature_file_full_path = os.path.abspath(signature_name)
            logging.debug('Writing to sig: %s', signature_file_full_path)
            file.write(signature_file_full_path, signature_name)
        else:
            raise ValueError('The signature file does not exist')
        file.write(filename_full_path, filename)
    try:
        logging.info('Deleting existing csar file with the name: %s', filename)
        os.remove(filename)
    except OSError:
        logging.debug('No existing csar file to delete')


def generate_func(args):
    """Generate command

    :param args: Command line arguments
    """
    with TemporaryDirectory(dir='.') as tempdir:
        generate.create_source(tempdir, args)
        vnfd_path = generate.get_vnfd(tempdir, args)

        if args.no_images:
            logging.info('Lightweight CSAR requested, skipping docker.tar file generation')
            generate.empty_images_section(tempdir)
        elif args.images:
            logging.info('docker.tar file has been passed in, skipping docker.tar file generation')
            docker_file = generate.create_docker_tar_link(tempdir, args.images)
            generate.create_images_section(tempdir, docker_file)
        else:
            logging.info('Generating the docker.tar file')
            docker_file = generate.create_docker_tar(tempdir, args)
            generate.create_images_section(tempdir, docker_file)
            generate_hash_for_docker_tar(tempdir, vnfd_path, docker_file)

        if args.pkgOption == '2':
            generate_option2(tempdir, args, vnfd_path)
        else:
            generate_option1(tempdir, args, vnfd_path)

    if args.product_report:
        try:
            product_report.csar_product_report(args)
        except product_report.ProductReportError as exc:
            logging.error(exc)
            sys.exit(1)


def generate_hash_for_docker_tar(directory, vnfd_path, docker_file):
    """Generate hash for Docker tar

    :param directory: CSAR packaging directory
    :param vnfd_path: Path to VNFD file
    :param docker_file: Docker tar file
    """
    full_vnfd_path = os.path.join(directory, vnfd_path)
    with open(full_vnfd_path, 'r+', encoding='utf-8') as values_file:
        vnfd_dict = safe_load(values_file)
        try:
            if isinstance(vnfd_dict, dict) and \
                    vnfd_dict.get('tosca_definitions_version') == 'tosca_simple_yaml_1_3':
                logging.info('Csar vnfd version is 1.3 - '
                             'starting to generate hashes for software_images artifacts')
                calculate_and_write_hash_for_docker_tar(vnfd_dict, docker_file)
                updated_vnfd = dump(vnfd_dict, sort_keys=False)
                values_file.seek(0)
                values_file.write(updated_vnfd)
                values_file.truncate()
        except (IOError, YAMLError):
            logging.exception('Failed to fill hash values for docker.tar artifact')


def calculate_and_write_hash_for_docker_tar(vnfd_dict, docker_file):
    """Calculate hash for Docker tar file

    :param vnfd_dict: VNFD definition dictionary
    :param docker_file: Docker tar file
    """
    if not isinstance(vnfd_dict['node_types'], dict):
        logging.error('Wrong structure, node_types is not a dictionary '
                      'or node_types is not present')
        return

    if 'node_types' not in vnfd_dict:
        logging.error('No node_types in VNFd dictionary')
        return

    for node_type_name, node_type in vnfd_dict['node_types'].items():
        try:
            checksum = node_type['artifacts']['software_images']['properties']['checksum']
        except KeyError:
            logging.error('Failed to get checksum')
            return

        logging.info('Filling hash value for docker.tar artifact in %s node type',
                     node_type_name)
        hash_algorithm = checksum.get('algorithm')

        if hash_algorithm not in hash_utils.HASH:
            logging.error('Failed to generate hash for docker.tar artifact '
                          'in %s node type because algorithm is not specified '
                          'or is not recognized', node_type_name)
            return

        logging.info('Calculating hash for docker.tar artifact in %s node type '
                     'using %s algorithm', node_type_name, hash_algorithm)
        checksum_hash = hash_utils.HASH[hash_algorithm](docker_file)
        checksum['hash'] = checksum_hash


def parse_args(args_list):
    """
    CLI entry point
    """

    parser = argparse.ArgumentParser(description='CSAR File Utilities')

    subparsers = parser.add_subparsers(help='generate')
    generate_parser = subparsers.add_parser('generate')
    generate_parser.set_defaults(func=generate_func)
    generate_parser.add_argument(
        '--docker-config',
        help='''Path to Docker configuration''',
        default='/root/.docker'
    )
    generate_parser.add_argument(
        '--timeout',
        help='Docker pull operation timeout',
        default=600
    )
    generate_parser.add_argument(
        '-hm',
        '--helm',
        type=utils.valid_file,
        help='One or more Helm charts to use to generate the csar file. '
             'This can be absolute paths or relative to the the current folder',
        nargs='*'
    )
    generate_parser.add_argument(
        '-hd',
        '--helm-dir',
        type=utils.valid_directory,
        help='''A directory containing the helm charts'''
    )
    generate_parser.add_argument(
        '-hf',
        '--helmfile',
        type=utils.valid_file,
        help='One Helmfile to use to generate the csar file. '
             'This can be absolute paths or relative to the the current folder',
        nargs='*'
    )
    generate_parser.add_argument(
        '-n',
        '--name',
        help='The name to give the generated CSAR file',
        required=True
    )
    generate_parser.add_argument(
        '-sc',
        '--scripts',
        type=utils.valid_directory,
        help='the path to a folder which contains scripts to be included in the CSAR file'
    )
    generate_parser.add_argument(
        '-l',
        '--log',
        help='Change the logging level for this execution, default is INFO',
        default='INFO'
    )
    generate_parser.add_argument(
        '--set',
        help='Values to be passed to the helm template during CSAR package generation',
        nargs='*'
    )
    generate_parser.add_argument(
        '-f',
        '--values',
        help='Yaml file containing values to be passed to the helm template during '
             'CSAR package generation',
        nargs='*'
    )
    generate_parser.add_argument(
        '-hs',
        '--history',
        help='The path to the change log for the CSAR file',
        default=''
    )
    generate_parser.add_argument(
        '-lcs',
        '--licenses',
        help='The path to the licenses directory for the CSAR file',
        type=utils.valid_directory
    )
    generate_parser.add_argument(
        '-lc',
        '--license',
        help='The path to the license files for the CSAR file',
        type=utils.valid_file,
        nargs='*'
    )
    values_group = generate_parser.add_mutually_exclusive_group()
    values_group.add_argument(
        '-mf',
        '--manifest',
        type=utils.valid_file,
        help='The path to the manifest file for the CSAR file.'
    )
    values_group.add_argument(
        '-vc',
        '--values-csar',
        type=utils.valid_file,
        help='The path to the yaml file containing values for generating '
             'manifest for CSAR package'
    )
    generate_parser.add_argument(
        '-vn',
        '--vnfd',
        type=utils.valid_file,
        help='The path to the VNF Descriptor yaml file for the CSAR file'
    )
    generate_parser.add_argument(
        '-d',
        '--definitions',
        type=utils.valid_path,
        help='The path to an additional definitions file or a directory '
             'containing definition files'
    )
    generate_parser.add_argument(
        '-sm',
        '--scale-mapping',
        type=utils.valid_file,
        help='The path to a scale-mapping file.',
    )
    generate_parser.add_argument(
        '-vcd',
        '--values-cnf-dir',
        type=utils.valid_path,
        help='The path to a directory with cnf values files. '
             'Values files should have the same name as a chart.'
    )
    generate_parser.add_argument(
        '-vcf',
        '--values-cnf-file',
        type=utils.valid_file,
        help='The path to cnf values yaml file. '
             'Values yaml file should have the same name as a chart.',
        nargs='*'
    )
    generate_parser.add_argument(
        '--sha512',
        type=convert_str_to_bool,
        help='Boolean to generate SHA512 hash for each file in the CSAR file '
             'and write to manifest file if provided.',
        default=True
    )
    generate_parser.add_argument(
        '-cert',
        '--certificate',
        type=utils.valid_file,
        help='The certificate file for signing of the CSAR'
    )
    generate_parser.add_argument(
        '--key',
        type=utils.valid_file,
        help='Private key file for signing of the CSAR'
    )
    generate_parser.add_argument(
        '--images',
        type=utils.valid_file,
        help='The path to a pre-packaged file containing the container images '
             'exported from the Helm chart',
        default=None
    )
    generate_parser.add_argument(
        '--no-images',
        help='Flag to skip generation of the docker.tar file',
        action='store_true'
    )
    generate_parser.add_argument(
        '--pkgOption',
        help='To generate signed VNF package, 1 for Option1 and 2 for Option2. '
             'Set to 1 by default',
        default='1',
        type=str
    )
    generate_parser.add_argument(
        '--sol-version',
        help='SOL version. Version of ETSI GS NFV-SOL 004. String format example: 3.3.1',
        type=str
    )
    generate_parser.add_argument(
        '--helm3',
        action='store_true',
        help='To generate CSAR with Helm 3'
    )
    generate_parser.add_argument(
        '--helm-version',
        help='Helm3 version to use',
        choices=SUPPORTED_HELM3_VERSIONS
    )
    generate_parser.add_argument(
        '--helm-debug',
        action='store_true',
        help='Run helm commands with debug option'
    )
    generate_parser.add_argument(
        '--product-report',
        help='To generate product report YAML file'
    )
    generate_parser.add_argument(
        '--is-upgrade',
        action='store_true',
        help='To upgrade product'
    )
    generate_parser.add_argument(
        '--eric-product-info',
        action='store_true',
        help='To parse eric-product-info.yaml to get images'
    )
    generate_parser.add_argument(
        '--agentk',
        action='store_true',
        default=False,
        help='Enable Agent K'
    )
    generate_parser.add_argument(
        '--disable-helm-template',
        action='store_true',
        default=False,
        help='Disable Helm template usage. Prints out a warning if '
             'for successful operation would be needed.'
    )
    generate_parser.add_argument(
        '--eric-product-info-charts',
        type=utils.valid_file,
        help='The list of path to Helm charts that '
             'eric-product-info.yaml has to be parsed to get images',
        nargs='*'
    )
    generate_parser.add_argument(
        '--extract-crds',
        action='store_true',
        help='Extract CRDs from Helm charts to be packaged separately.'
    )

    args = parser.parse_args(args_list)
    __check_arguments(parser, args)
    return args


def convert_str_to_bool(arg):
    """Argparse type for converting string to bool

    :param arg: Argument
    :raises argparse.ArgumentTypeError: Unexpected input value
    :return: Converted boolean value
    """
    if arg.lower() in ('true', 't'):
        return True
    if arg.lower() in ('false', 'f'):
        return False

    raise argparse.ArgumentTypeError('Boolean value expected.')


def __configure_logging(level):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=level.upper())


def main():
    """Main function"""
    args = parse_args(sys.argv[1:])
    __configure_logging(args.log)
    args.func(args)


if __name__ == '__main__':
    main()
