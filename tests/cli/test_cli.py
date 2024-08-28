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
import os
import tempfile

import pytest
import argparse
import tarfile

from eric_am_package_manager.cli import __main__
from eric_am_package_manager.generator import utils, generate
from eric_am_package_manager.generator.cnf_values_file_exception import CnfValuesFileException

SOL_VERSION = '2.5.1'

ROOT_DIR = os.path.abspath(os.path.join((os.path.abspath(__file__)), os.pardir))
RESOURCES_DIR = HELM = os.path.join(ROOT_DIR, os.pardir, 'resources')
HELM = os.path.join(ROOT_DIR, os.pardir, 'resources', 'helm')
HELMFILE1 = os.path.join(ROOT_DIR, os.pardir, 'resources', 'helmfile1')
HELMFILE2 = os.path.join(ROOT_DIR, os.pardir, 'resources', 'helmfile2')
INVALID_HELMFILE = os.path.join(ROOT_DIR, os.pardir, 'resources', 'invalid_helmfile.tgz')
EMPTY_HELM_DIR = os.path.join(ROOT_DIR, os.pardir, 'resources', 'no_helm_charts')
SCRIPTS = os.path.join(ROOT_DIR, os.pardir, 'resources', 'script')
VNFD = os.path.join(ROOT_DIR, os.pardir, 'resources', 'acceptance.yaml')
MF = os.path.join(ROOT_DIR, os.pardir, 'resources', 'acceptance.mf')
NOT_MATCHING_MF = os.path.join(ROOT_DIR, os.pardir, 'resources', 'acceptance2.mf')
KEY = os.path.join(ROOT_DIR, os.pardir, 'resources', 'acceptance-type2.key')
CERT = os.path.join(ROOT_DIR, os.pardir, 'resources', 'acceptance-type2.cert')
VALUES_CNF_FILE_PATH = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values')
VALUES_CNF_DIR_PATH = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values_correct')
VALUES_CNF_FILE = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values', 'values_cnf.yaml')
PATH_TO_LICENSES = os.path.join(ROOT_DIR, os.pardir, 'resources/Files/Licenses')
PATH_TO_LICENSE = os.path.join(ROOT_DIR, os.pardir, 'resources/Files/Licenses/License.txt')
PATH_TO_LOG_FILE = os.path.join(ROOT_DIR, os.pardir, 'resources', 'ChangeLog.txt')
VALUES_CNF_FILE_2 = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values_correct',
                                 'values_cnf_2.yaml')
VALUES_CNF_FILE_EMPTY = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values',
                                     'values_cnf_empty.yaml')
VALUES_CNF_FILE_4 = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values', 'values_cnf_4.yaml')
VALUES_CNF_FILE_INVALID = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values',
                                       'values_cnf_invalid.yaml')
VALUES_CNF_FILE_IGNORE = os.path.join(ROOT_DIR, os.pardir, 'resources/cnf_values',
                                      'values_cnf_ignore.yml')
VALUES_CSAR = os.path.join(ROOT_DIR, os.pardir, 'resources', 'values_csar.yaml')
VALUES_CSAR_INVALID = os.path.join(ROOT_DIR, os.pardir, 'resources', 'values_csar_invalid.yaml')
DEF_DIR = os.path.join(ROOT_DIR, os.pardir, 'resources', 'definitions')
DEF_FILE = os.path.join(DEF_DIR, 'types-definitions.yaml')
REPORT_OUT = os.path.join(ROOT_DIR, 'product-report.yaml')


@pytest.fixture(name='default_args')
def args():
    return ['generate', '--helm', HELM, '--name', 'name']


def test_main(capsys):
    with pytest.raises(SystemExit):
        args = __main__.parse_args(['generate', '-h'])
        args.func(args)
    out, _ = capsys.readouterr()
    assert out.startswith('usage:')


def test_check_arguments_no_valid_helm(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--helm', 'non_existent', '--name', 'name']
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "argument -hm/--helm: The value [non_existent] provided is not a valid file path, or it is not accessible for the user" in err


def test_check_arguments_no_valid_helmfile(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--helm', HELM, '--helmfile', HELMFILE1, '--name', 'name', '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "Cannot use --helm/--helm_dir and --helmfile together" in err


def test_check_arguments_no_valid_multiple_helmfile(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--helmfile', HELMFILE1, HELMFILE2, '--name', 'name', '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "More than 1 helmfile archives are not allowed" in err


def test_not_valid_helmfile(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--helmfile', INVALID_HELMFILE, '--name', 'name', '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "Provided helmfile archive is not a valid helmfile." in err


def test_check_arguments_no_helm_provided(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--name', 'name', '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "--helm or --helm-dir is required" in err


def test_check_arguments_no_helm_charts_in_directory(capsys):
    with pytest.raises(SystemExit):
        args = ['generate', '--helm-dir', EMPTY_HELM_DIR, '--name', 'name',
                '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "The specified directory does not contain any helm charts" in err


def test_check_arguments_helm_charts_not_directory(capsys):
    with pytest.raises(SystemExit):
        args = [
            'generate', '--helm-dir', 'non_existent', '--name', 'name',
            '--sol-version', SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "argument -hd/--helm-dir: The value [non_existent] provided is not a valid directory path, or it is not accessible for the user." in err


def test_check_arguments_multiple_helm_charts(capsys):
    with pytest.raises(SystemExit):
        args = [
            'generate', '--helm', HELM, 'non_existent', '--name', 'name', '--sol-version',
            SOL_VERSION]
        __main__.parse_args(args)
    _, err = capsys.readouterr()
    assert "argument -hm/--helm: The value [non_existent] provided is not a valid file path, or it is not accessible for the user." in err


def test_check_arguments_no_valid_scale_mapping(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--definitions', DEF_DIR, '--scale-mapping', 'non_existent'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument -sm/--scale-mapping: The value [non_existent] provided is not a valid file path, or it is not accessible for the user." in err


def test_check_arguments_no_valid_scripts(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--scripts', 'non_existent'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument -sc/--scripts: The value [non_existent] provided is not a valid directory path, or it is not accessible for the user." in err


def test_check_arguments_cert_with_no_manifest_or_values_csar(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--certificate', CERT, '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "A valid manifest file must be provided if certificate is provided." in err


def test_check_arguments_different_vnfd_and_manifest_names(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--vnfd', VNFD, '--manifest', NOT_MATCHING_MF, '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "The name of both VNFD yaml file and manifest file must match." in err


def test_check_arguments_no_valid_key(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--scripts', SCRIPTS, '--manifest', MF, '--key', 'non_existent', '--certificate',
             CERT])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument --key: The value [non_existent] provided is not a valid file path, or it is not accessible for the user." in err


def test_check_arguments_no_valid_cert_extension_option_2(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--manifest', MF, '--key', KEY, '--certificate',
             os.path.join(RESOURCES_DIR, 'spider-app.crt'),
             '--pkgOption', '2', '--name', 'spider-app', '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert 'Certificate extension must be \'.cert\'.' in err


def test_check_arguments_no_valid_cert_extension_option_1(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--manifest', MF, '--key', KEY, '--certificate',
             os.path.join(RESOURCES_DIR, 'spider-app.crt'),
             '--pkgOption', '1', '--name', 'spider-app', '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert 'Certificate extension must be \'.cert\'.' in err


def test_check_arguments_extension_and_cert_not_match_option_2(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--manifest', MF, '--key', KEY, '--certificate',
             os.path.join(RESOURCES_DIR, 'spider-app-invalid.cert'),
             '--pkgOption', '2', '--name', 'spider-app', '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "Certificate name and csar name must match for Option 2." in err


def test_check_arguments_option2_no_valid_cert(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--scripts', SCRIPTS, '--manifest', MF, '--key', 'non_existent', '--pkgOption', '2'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument --key: The value [non_existent] provided is not a valid file path, or it is not accessible for the user." in err


def test_check_arguments_option2_no_valid_key(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(
            ['--scripts', SCRIPTS, '--manifest', MF, '--certificate', CERT, '--pkgOption', '2',
             '--sol-version', SOL_VERSION])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "A valid certificate and key is not provided for Option 2" in err


def test_check_arguments_with_valid_args_passes_with_manifest_file(default_args):
    default_args.extend(['--scripts', SCRIPTS, '--vnfd', VNFD, '--manifest', MF, '--key', KEY,
                         '--certificate', CERT, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_valid_args_passes_with_values_csar_file(default_args):
    default_args.extend(['--values-csar', VALUES_CSAR, '--definitions', DEF_FILE,
                         '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_valid_args_passes_and_path_to_images(default_args, tmp_path):
    images = tmp_path / 'images.tar'
    images.touch()
    default_args.extend(['--images', str(images), '--definitions', DEF_FILE,
                         '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_nonexistent_images(default_args, capsys):
    default_args.extend(['--images', 'non_existent'])
    with pytest.raises(SystemExit):
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument --images: The value [non_existent] provided is not a valid file path, or it is not accessible for the user." in err


def test_convert_str_to_bool_true_and_false():
    low_true = 'true'
    cap_true = 'TRUE'
    low_false = 'false'
    cap_false = 'FALSE'
    assert __main__.convert_str_to_bool(low_true)
    assert __main__.convert_str_to_bool(cap_true)
    assert not __main__.convert_str_to_bool(low_false)
    assert not __main__.convert_str_to_bool(cap_false)


def test_convert_str_to_bool_non_bool_number():
    with pytest.raises(argparse.ArgumentTypeError):
        numbers = "3462786"
        __main__.convert_str_to_bool(numbers)


def test_convert_str_to_bool_non_bool_word():
    with pytest.raises(argparse.ArgumentTypeError):
        letters = "somelettersthataren'taboolean"
        __main__.convert_str_to_bool(letters)


def test_values_csar_validity(default_args, capsys):
    default_args.extend(["--values-csar", VALUES_CSAR_INVALID, '--sol-version', SOL_VERSION])
    with pytest.raises(SystemExit):
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "The specified values-csar yaml file does not contain all the required keys" in err


def test_check_arguments_no_valid_definitions(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--definitions', 'non_existent'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument -d/--definitions: The value [non_existent] provided is not a valid path, or it is not accessible for the user." in err


def test_check_arguments_with_valid_definition_directory_passes(default_args):
    default_args.extend(['--definitions', DEF_DIR, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_valid_definition_file_passes(default_args):
    default_args.extend(['--definitions', DEF_FILE, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_both_values_csar_and_manifest_files(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--manifest', MF, '--values-csar', VALUES_CSAR])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument -vc/--values-csar: not allowed with argument -mf/--manifest" in err


def test_check_arguments_with_valid_product_report_file(default_args):
    default_args.extend(['--product-report', REPORT_OUT, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_valid_helm_version(default_args):
    default_args.extend(['--helm-version', '3.8.2', '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_invalid_helm_version(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--helm-version', '1.2.3'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "--helm-version: invalid choice: '1.2.3'" in err


def test_check_is_valid_values_cnf_format():
    assert utils.is_yaml_format_file(VALUES_CNF_FILE)


def test_check_load_invalid_values_cnf_file():
    with pytest.raises(CnfValuesFileException) as msg:
        utils.is_cnf_yaml_file_correct(VALUES_CNF_FILE_INVALID)
    assert 'File values_cnf_invalid could not be loaded: mapping values are not allowed here' \
           in str(msg.value)


def test_check_invalid_values_cnf_format():
    with pytest.raises(CnfValuesFileException) as msg:
        utils.is_yaml_format_file(VALUES_CNF_FILE_EMPTY)
    assert "Cnf values file is empty" in str(msg.value)


def test_check_ignore_values_cnf_file():
    assert not utils.is_yaml_format_file(VALUES_CNF_FILE_IGNORE)


def test_check_is_cnf_yaml_file_correct():
    assert utils.is_cnf_yaml_file_correct(VALUES_CNF_FILE)


def test_get_chart_base_names():
    test_list = ["/test/path/file.txt", "/test/path/file2.txt"]
    names = utils.get_chart_base_names(test_list)
    assert names.__contains__("file.txt")
    assert names.__contains__("file2.txt")
    assert names.__len__().__eq__(2)


def test_is_chart_in_list_product_info_charts_true():
    mock_args = argparse.Namespace(eric_product_info_charts=["path/file.txt"])
    assert utils.is_chart_in_list_product_info_charts(mock_args, "/test/path/file.txt")


def test_is_chart_in_list_product_info_charts_false():
    mock_args = argparse.Namespace(eric_product_info_charts=["path/file.txt"])
    assert not utils.is_chart_in_list_product_info_charts(mock_args, "/test/path/file2.txt")


def test_check_is_cnf_yaml_file_not_correct():
    with pytest.raises(CnfValuesFileException) as err:
        utils.is_cnf_yaml_file_correct(VALUES_CNF_FILE_INVALID)
    assert "File values_cnf_invalid could not be loaded: mapping values are not allowed here" \
           in str(err.value)


def test_check_is_cnf_yaml_file_not_found():
    with pytest.raises(FileNotFoundError) as err:
        utils.is_cnf_yaml_file_correct("not_a_file")
    assert "File not_a_file not available: [Errno 2] No such file or directory: 'not_a_file'" \
           in str(err.value)


def test_check_arguments_cert_with_no_values_cnf_file(default_args, capsys):
    with pytest.raises(SystemExit):
        default_args.extend(['--values-cnf-dir', 'non_existent'])
        __main__.parse_args(default_args)
    _, err = capsys.readouterr()
    assert "argument -vcd/--values-cnf-dir: The value [non_existent] provided" \
           " is not a valid path, or it is not accessible for the user." in err


def test_check_arguments_with_values_cnf_file(default_args, capsys):
    default_args.extend(['--values-cnf-dir', VALUES_CNF_FILE, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_licenses(default_args, capsys):
    default_args.extend(['--licenses', PATH_TO_LICENSES, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_license(default_args, capsys):
    default_args.extend(['--license', PATH_TO_LICENSE, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_history(default_args, capsys):
    default_args.extend(['--history', PATH_TO_LOG_FILE, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_check_arguments_with_eric_product_info_charts(default_args, capsys):
    default_args.extend(['--eric-product-info-charts', HELM, '--sol-version', SOL_VERSION])
    __main__.parse_args(default_args)


def test_put_cnf_values_to_chart_path_error():
    with pytest.raises(CnfValuesFileException) as err:
        with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
            mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH)
            helm_dict = {}
            cnf_dict = generate.get_values_cnf_dict(mock_args)
            generate.put_cnf_values_to_chart_path(temp_directory, cnf_dict, helm_dict)
    assert 'There is not matching Helm chart for values file values_cnf' in str(err.value)


def test_put_cnf_values_to_chart_path():
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
        mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH)
        helm_dict = generate.get_values_cnf_dict(mock_args)
        cnf_dict = generate.get_values_cnf_dict(mock_args)
        generate.put_cnf_values_to_chart_path(temp_directory, cnf_dict, helm_dict)
        assert os.listdir(temp_directory).__len__().__eq__(3)


def test_add_cnf_value_to_chart_path():
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
        mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH,
                                       values_cnf_file=[VALUES_CNF_FILE])
        helm_dict = generate.get_values_cnf_dict(mock_args)
        generate.add_cnf_values_to_chart_path(mock_args, temp_directory, helm_dict)
        assert os.listdir(temp_directory).__len__().__eq__(1)


def test_add_cnf_value_to_chart_path_multiple():
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
        mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH,
                                       values_cnf_file=[VALUES_CNF_FILE, VALUES_CNF_FILE_2])
        helm_dict = generate.get_values_cnf_dict(mock_args)
        generate.add_cnf_values_to_chart_path(mock_args, temp_directory, helm_dict)
        assert os.listdir(temp_directory).__len__().__eq__(2)


def test_add_cnf_values_by_both_types_error():
    with pytest.raises(CnfValuesFileException) as err:
        with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
            mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH,
                                           values_cnf_file=[VALUES_CNF_FILE, VALUES_CNF_FILE_2])
            helm_dict = generate.get_values_cnf_dict(mock_args)
            generate.add_cnf_values_dir_to_chart_path(mock_args, temp_directory, helm_dict)
            generate.add_cnf_values_to_chart_path(mock_args, temp_directory, helm_dict)
    assert 'Cannot add CNF values file values_cnf to chart path due to: File exists' \
           in str(err.value)


def test_add_cnf_values_by_both_types():
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
        mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_DIR_PATH,
                                       values_cnf_file=[VALUES_CNF_FILE_4])
        helm_dict = generate.get_values_cnf_dict(mock_args)
        helm_dict["values_cnf_4"] = "/path"
        generate.add_cnf_values_dir_to_chart_path(mock_args, temp_directory, helm_dict)
        generate.add_cnf_values_to_chart_path(mock_args, temp_directory, helm_dict)
        assert os.listdir(temp_directory).__len__().__eq__(4)


def test_add_cnf_values_with_helm_dir_param():
    with tempfile.TemporaryDirectory(dir=ROOT_DIR) as temp_directory:
        helm_path = os.path.join(temp_directory, 'Helm')
        os.mkdir(helm_path)
        mock_args = argparse.Namespace(helm_dir=helm_path,
                                       values_cnf_file=[VALUES_CNF_FILE_4])
        with open(helm_path + '/values_cnf_4.tgz', 'w') as file:
            file.write('')
            pass
        helm_chart_dict = {}
        generate.add_helm_dir_to_chart_path(mock_args, temp_directory, helm_chart_dict)
        generate.add_cnf_values_to_chart_path(mock_args, temp_directory, helm_chart_dict)
        assert os.listdir(temp_directory).__len__().__eq__(3)


def test_get_values_cnf_dict(default_args):
    mock_args = argparse.Namespace(values_cnf_dir=VALUES_CNF_FILE_PATH)
    cnf_dict = generate.get_values_cnf_dict(mock_args)
    assert cnf_dict.__len__().__eq__(5)


def test_get_values_cnf_dict_error(default_args):
    with pytest.raises(FileNotFoundError) as err:
        mock_args = argparse.Namespace(values_cnf_dir="")
        generate.get_values_cnf_dict(mock_args)
    assert "[Errno 2] No such file or directory: ''" in str(err.value)


def test_is_archive_helmfile_positive(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("archives")
    tgz_filename = temp_dir / 'test_archive.tgz'
    helmfile_path = temp_dir / 'helmfile.yaml'
    helmfile_path.write_text('Content of helmfile.yaml')
    with tarfile.open(tgz_filename, 'x:gz') as tgz:
        tgz.add(name=helmfile_path, arcname="helmfile.yaml")
    args = __main__.parse_args(['generate', '--helmfile', str(tgz_filename), '--name', 'name',
                                '--sol-version', SOL_VERSION])
    result = __main__.is_valid_helmfile(args)
    assert result