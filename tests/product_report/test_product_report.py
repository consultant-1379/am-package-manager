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
"""Unit tests for Product Report"""

import argparse
import os
import sys
from unittest.mock import patch, ANY
from tempfile import NamedTemporaryFile
import pytest

from eric_am_package_manager.generator import product_report
from eric_am_package_manager.generator.utils import load_yaml_file

ROOT_DIR = os.path.abspath(os.path.join((os.path.abspath(__file__)),
                                        os.pardir, os.pardir))
RESOURCES = os.path.abspath(os.path.join(ROOT_DIR, 'resources'))


@pytest.fixture(name="mock_args")
def default_args():
    return argparse.Namespace(docker_config="",
                              helm3=True,
                              helm_debug=False,
                              helm_version="",
                              helm_options="",
                              product_report="asdf.yaml",
                              disable_helm_template=True,
                              values=None,
                              no_images=True)


@pytest.fixture(name="mock_helmfile_args")
def default_helmfile_args():
    return argparse.Namespace(docker_config="",
                              helm3=True,
                              helm_debug=False,
                              helm_version="",
                              helm_options="",
                              product_report="asdf.yaml",
                              eric_product_info=True,
                              values=None,
                              no_images=True)


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_helm_metadata_with_ok_chart_and_ok_epi(_, docker, labels, config, manifest_hash, mock_args):
    manifest_hash.return_value = '4833bd871d80f9cc2e6dbe52131942562922b43e322ebfeded43e18dae883d16'
    docker.return_value = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='CXC1742971',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='4833bd871d80f9cc2e6dbe52131942562922b43e322ebfeded43e1'
                  '8dae883d16')

    path = os.path.join(RESOURCES, "helmdirs/eric-sec-sip-tls-crd")
    helm = product_report.HelmChart(path,
                                    "eric-sec-sip-tls-crd",
                                    sha256sum='aaaa',
                                    include_helm=True)
    helm.parse()
    charts, images = helm.get_components()
    assert len(charts) == 1
    assert len(images) == 1
    assert not helm.get_errors()
    assert not helm.get_warnings()

    assert {'chart_name': 'eric-sec-sip-tls-crd',
            'chart_version': '2.8.0+35',
            'product_version': '2.8.0',
            'product_number': 'CXC1742970',
            'package': 'eric-sec-sip-tls-crd',
            'sha256sum': 'aaaa'} in charts

    assert {'image': 'armdocker.rnd.ericsson.se/proj-common-assets-cd/'
                     'security/eric-sec-sip-tls-crd-job:2.8.0-35',
            'product_number': 'CXC1742971',
            'product_version': '2.8.0',
            'image_name': 'eric-sec-sip-tls-crd-job',
            'image_tag': '2.8.0-35',
            'sha256sum': '4833bd871d80f9cc2e6dbe52131942562922b43e322e'
                         'bfeded43e18dae883d16'} in images


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_helm_metadata_with_ok_chart_and_nok_labels(_, docker, labels, config, manifest_hash, mock_args):
    manifest_hash.return_value = '4833bd871d80f9cc2e6dbe52131942562922b43e322ebfeded43e18dae883d16'
    docker.return_value = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='4833bd871d80f9cc2e6dbe52131942562922b43e322ebfeded43e'
                  '18dae883d16')

    path = os.path.join(RESOURCES, "helmdirs/eric-sec-sip-tls-crd")
    helm = product_report.HelmChart(path,
                                    "eric-sec-sip-tls-crd",
                                    sha256sum='aaaa',
                                    include_helm=True)
    helm.parse()
    charts, images = helm.get_components()
    assert len(charts) == 1
    assert len(images) == 1
    assert not helm.get_warnings()
    assert any("Image labels not matching" in s for s in
               helm.get_errors()["eric-sec-sip-tls-crd"])

    assert {'chart_name': 'eric-sec-sip-tls-crd',
            'chart_version': '2.8.0+35',
            'product_version': '2.8.0',
            'product_number': 'CXC1742970',
            'package': 'eric-sec-sip-tls-crd',
            'sha256sum': 'aaaa'} in charts

    assert {'image': 'armdocker.rnd.ericsson.se/proj-common-assets-cd/'
                     'security/eric-sec-sip-tls-crd-job:2.8.0-35',
            'product_number': 'CXC1742971',
            'product_version': '2.8.0',
            'image_name': 'eric-sec-sip-tls-crd-job',
            'image_tag': '2.8.0-35',
            'sha256sum': '4833bd871d80f9cc2e6dbe52131942562922b43e322e'
                         'bfeded43e18dae883d16'} in images


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_helm_metadata_with_ok_helm_chart(_, docker, labels, config, manifest_hash, mock_args):
    manifest_hash.return_value = 'ffff'
    path = os.path.join(RESOURCES, "helmdirs/eric-cloud-native-base")

    expected = [
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-common-assets-cd-released/'
                  'control/cm/eric-cm-mediator/eric-cm-mediator:7.6.0-11',
            image_tag='7.6.0-11',
            product_version='7.6.0',
            product_number='CXC2011452',
            image_name='eric-cm-mediator',
            sha256sum='ffff'),
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-common-assets-cd-released/'
                  'control/cm/eric-cm-mediator/eric-cm-key-init:7.6.0-11',
            image_tag='7.6.0-11',
            product_version='7.6.0',
            product_number='CXC1742649',
            image_name='eric-cm-key-init',
            sha256sum='ffff'),
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-common-assets-cd-released/'
                  'control/cm/eric-cm-mediator/'
                  'eric-cm-mediator-init-container:7.6.0-11',
            image_tag='7.6.0-11',
            product_version='7.6.0',
            product_number='CXU1010357',
            image_name='eric-cm-mediator-init-container',
            sha256sum='ffff'),
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-adp-eric-ctrl-bro-drop/'
                  'eric-ctrl-bro:4.7.0-23',
            image_tag='4.7.0-23',
            product_version='4.7.0',
            product_number='CXC2012182',
            image_name='eric-ctrl-bro',
            sha256sum='ffff')
    ]
    docker.side_effect = expected

    helm = product_report.HelmChart(path,
                                    "eric-cloud-native-base",
                                    sha256sum='ffff',
                                    include_helm=True)
    helm.parse()
    charts, images = helm.get_components()
    assert len(charts) == 1
    assert len(images) == 4
    assert not helm.get_errors()
    assert not helm.get_warnings()

    assert {'chart_name': 'eric-cloud-native-base',
            'chart_version': '1.50.0',
            'product_version': '1.50.0',
            'product_number': 'CXD101001',
            'package': 'eric-cloud-native-base',
            'sha256sum': 'ffff'} in charts

    for image in expected:
        assert image in images


@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_helm_metadata_with_no_helm_charts(_, parse_config, mock_args):
    path = os.path.join(RESOURCES, "no_helm_charts")
    helm = product_report.HelmChart(path,
                                    "",
                                    sha256sum='',
                                    include_helm=True)
    helm.parse()
    charts, images = helm.get_components()
    assert len(charts) == 1
    assert len(images) == 0
    assert helm.get_errors()

    assert {'chart_name': '',
            'chart_version': '',
            'product_version': '',
            'product_number': '',
            'package': '',
            'sha256sum': ''} in charts


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.product_report.sha256')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.product_report.extract')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_report(_, docker, labels, mock_extract, config, mock_sha256, manifest_hash, mock_args):
    mock_sha256.return_value = 'ffff'
    manifest_hash.return_value = 'ffff'
    expected_image = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='CXC1742971',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='ffff')

    expected_chart = product_report.HelmData(
        product_number="CXC1742970",
        product_version="2.8.0",
        package="path",
        chart_name="eric-sec-sip-tls-crd",
        chart_version="2.8.0+35",
        sha256sum="ffff")

    docker.return_value = expected_image
    mock_extract.return_value.__enter__.return_value = \
        os.path.join(RESOURCES, "helmdirs/eric-sec-sip-tls-crd")

    with NamedTemporaryFile() as temp:
        mock_args.product_report = temp.name
        product_report.create_product_report(mock_args,
                                             ["/helm/path"])
        report = load_yaml_file(temp.name)
        assert expected_image in report["includes"]["images"]
        assert expected_chart in report["includes"]["packages"]


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_helmfile_metadata_with_ok_helmfile(_, docker, labels, config, manifest_hash, mock_args):
    manifest_hash.return_value = 'ffff'
    path = os.path.join(RESOURCES, "helmfiles/eric-eiae-helmfile")

    expected = [
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-orchestration-so/'
                  'keycloak-client:1.0.0-89',
            image_tag='1.0.0-89',
            product_version='1.0.0',
            product_number='TBC',
            image_name='keycloak-client',
            sha256sum='ffff'),
        product_report.ImageData(
            image='armdocker.rnd.ericsson.se/proj-adp-eric-data-object-storage-mn-released/'
                  'eric-data-object-storage-mn-init:2.5.0-15',
            image_tag='7.6.0-11',
            product_version='2.5.0',
            product_number='CXC1742824',
            image_name='eric-data-object-storage-mn-init',
            sha256sum='ffff'),
    ]
    docker.side_effect = expected

    helmfile = product_report.HelmChart(path,"eric-eiae-helmfile", sha256sum='ffff', include_helm=False)
    helmfile.parse()
    packages, images = helmfile.get_components()
    assert len(packages) == 0
    assert len(images) == 2


@pytest.mark.parametrize("helmfile, helmfile_sha256, expected_result", [
    ({'name': 'eric-eo-helmfile', 'version': '2.23.0-37'}, "ffff", [
        {
            "product_number": "TBC",
            "product_version": "2.23.0-37",
            "package": "eric-eo-helmfile-2.23.0-37.tgz",
            "helmfile_name": "eric-eo-helmfile",
            "helmfile_version": "2.23.0-37",
            "sha256sum": "ffff"
        }
    ]),
    ({'name': 'eric-eic-helmfile', 'version': '2.2222.0'}, "ffff", [
        {
            "product_number": "TBC",
            "product_version": "2.2222.0",
            "package": "eric-eic-helmfile-2.2222.0.tgz",
            "helmfile_name": "eric-eic-helmfile",
            "helmfile_version": "2.2222.0",
            "sha256sum": "ffff"
        }
    ]),
    ({'name': 'eric-eo-helmfile', 'version': '1.222.2022222-12'}, "ffff", [
        {
            "product_number": "TBC",
            "product_version": "1.222.2022222-12",
            "package": "eric-eo-helmfile-1.222.2022222-12.tgz",
            "helmfile_name": "eric-eo-helmfile",
            "helmfile_version": "1.222.2022222-12",
            "sha256sum": "ffff"
        }
    ]),
])
def test_write_helmfile_package_info_positive(helmfile, helmfile_sha256, expected_result):
    packages = product_report.get_helmfile_package_info(helmfile, helmfile_sha256)
    assert packages == expected_result


@pytest.mark.parametrize("helmfile, helmfile_sha256, expected_result", [
    ({}, "ffff", [
        {}
    ]),
    ({'name': 'eric-eo-helmfile', 'version': ''}, "ffff", [
        {}
    ]),
    ({'name': '', 'version': ''}, "ffff", [
        {}
    ]),
    ({'name': '', 'version': '2.23.0-37'}, "ffff", [
        {}
    ]),
])
def test_write_helmfile_package_info_negative(helmfile, helmfile_sha256, expected_result):
    with pytest.raises(product_report.ProductReportError):
        product_report.get_helmfile_package_info(helmfile, helmfile_sha256)


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.product_report.sha256')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.product_report.extract')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.product_report.HelmChart._parse_helm_template')
def test_report_failed_verification(_, docker, labels, mock_extract, parse_config, mock_sha256, get_manifest_hash, mock_args):
    mock_sha256.return_value = "ffff"
    get_manifest_hash.return_value = "ffff"

    invalid_image = product_report.ImageData(
        image='',
        product_number='',
        product_version='',
        image_name='',
        image_tag='',
        sha256sum='ffff')

    expected_image = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='CXC1742971',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='ffff')

    expected_chart = product_report.HelmData(
        product_number="CXC1742970",
        product_version="2.8.0",
        package="path",
        chart_name="eric-sec-sip-tls-crd",
        chart_version="2.8.0+35",
        sha256sum="ffff")

    docker.return_value = invalid_image
    mock_extract.return_value.__enter__.return_value = \
        os.path.join(RESOURCES, "helmdirs/eric-sec-sip-tls-crd")

    with NamedTemporaryFile() as temp:
        mock_args.product_report = temp.name
        with pytest.raises(product_report.ProductReportError):
            product_report.create_product_report(mock_args,
                                                 ["/helm/path"])
        report = load_yaml_file(temp.name)
        assert expected_image in report["includes"]["images"]
        assert expected_chart in report["includes"]["packages"]


@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_manifest_hash')
@patch('eric_am_package_manager.generator.product_report.sha256')
@patch('eric_am_package_manager.generator.docker_api.DockerConfig.parse_config')
@patch('eric_am_package_manager.generator.product_report.extract')
@patch('eric_am_package_manager.generator.docker_api.DockerApi.get_labels')
@patch('eric_am_package_manager.generator.product_report.ImageData.from_labels')
@patch('eric_am_package_manager.generator.helm_utils.check_output')
def test_helm_values(check_output, docker, labels, mock_extract, config, mock_sha256, manifest_hash, mock_args):
    mock_sha256.return_value = 'ffff'
    manifest_hash.return_value = 'ffff'

    mock_args.disable_helm_template = False
    mock_args.values = ["values.yaml"]

    expected_image = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='CXC1742971',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='ffff')

    expected_chart = product_report.HelmData(
        product_number="CXC1742970",
        product_version="2.8.0",
        package="path",
        chart_name="eric-sec-sip-tls-crd",
        chart_version="2.8.0+35",
        sha256sum="ffff")

    docker.return_value = expected_image
    mock_extract.return_value.__enter__.return_value = \
        os.path.join(RESOURCES, "helmdirs/eric-sec-sip-tls-crd")

    with NamedTemporaryFile() as temp:
        mock_args.product_report = temp.name
        product_report.create_product_report(mock_args,
                                             ["/helm/path"])
        report = load_yaml_file(temp.name)
        assert expected_image in report["includes"]["images"]
        assert expected_chart in report["includes"]["packages"]

        check_output.assert_called_with(['helm3',
                                         'template',
                                         '--values', 'values.yaml',
                                         ANY])


def test_remove_duplicate_images_with_same_sha():
    image = product_report.ImageData(
        image='armdocker.rnd.ericsson.se/proj-common-assets-cd/security/'
              'eric-sec-sip-tls-crd-job:2.8.0-35',
        product_number='CXC1742971',
        product_version='2.8.0',
        image_name='eric-sec-sip-tls-crd-job',
        image_tag='2.8.0-35',
        sha256sum='ffff')
    image2 = image
    image2["image"] = 'armdocker.rnd.ericsson.se/proj-common-assets-cd-released/'\
        'security/eric-sec-sip-tls-crd-job:2.8.0-35'
    components = {
        "images": [image, image2],
        "packages": []
    }
    product_report.remove_duplicates(components, archive_type="helm")
    assert len(components["images"]) == 1


if __name__ == "__main__":
    sys.exit(pytest.main(["-v --doctest-modules", __file__]))
