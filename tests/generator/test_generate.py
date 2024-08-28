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
import argparse
import os
from yaml import safe_load
from tempfile import TemporaryDirectory
from pathlib import Path

from eric_am_package_manager.generator import generate
from eric_am_package_manager.generator.image import Image
from eric_am_package_manager.generator.crd_handler import extract_crds
ROOT_DIR = os.path.abspath(os.path.join((os.path.abspath(__file__)), os.pardir))
RESOURCES = os.path.abspath(os.path.join(ROOT_DIR, os.pardir, 'resources'))
images = ["armdocker.rnd.ericsson.se/proj-orchestration-so/api-gateway:1.0.0-31",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/dashboard:1.0.2-3",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/eai-adapter:1.0.0-82",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/ecm-adapter:1.0.0-40",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/ecm-stub:1.0.0-26",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/engine:1.0.6-29",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/enm-adapter:1.0.0-61",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/enm-stub:1.0.0-42",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/eso-security:1.0.0-15",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/eso-workflow:1.0.0-36",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/onboarding:1.0.0-14",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/orchestration-gui:18.0.0-53",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/orchestrationcockpit:1.0.1-65",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/subsystems-manager:1.0.1-51",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/topology:1.0.1-33",
          "armdocker.rnd.ericsson.se/proj-orchestration-so/tosca:1.1.0",
          "dl360x3425.ete.ka.sw.ericsson.se:5000/sdpimages/eric-ec-sdp:1.0.0-090121"]


mock_args = argparse.Namespace(docker_config="", helm3=True, helm_debug=False, helm_version=None)


def generate_directory_structure(structure, outdir):
    for item, value in structure.items():
        if isinstance(value, dict):
            Path(outdir, item).mkdir(parents=True, exist_ok=True)
            generate_directory_structure(value, Path(outdir, item))
        else:
            Path(outdir, item).touch()


def test_split_images_no_empty_lines():
    image_list = generate.__parse_images(images)
    assert len(image_list) == 17


def test_split_images_no_empty_information():
    image_list = generate.__parse_images(images)
    for image in image_list:
        assert len(image.repo) != 0
        assert len(image.tag) != 0


def test_images_with_no_tags():
    images = ["armdocker.rnd.ericsson.se/proj-orchestration-so/eso-security:1.0.0-15",
              "armdocker.rnd.ericsson.se/proj-orchestration-so/eso-workflow",
              "armdocker.rnd.ericsson.se/proj-orchestration-so/onboarding:1.0.0-14"]
    image_list = generate.__parse_images(images)
    tags = []
    for image in image_list:
        tags.append(image.tag)
    tags.remove("latest")
    assert len(tags) == 2


def test_create_path():
    with TemporaryDirectory() as tempdir:
        test_string = generate.create_path(tempdir, '', 'a_destination')
        assert test_string == ''


def test_check_digest_with_manifest():
    true_sha_and_manifest = argparse.Namespace(sha512=True, manifest='aManifest', values_csar='')
    assert generate.check_digest(true_sha_and_manifest) == 'SHA-512'


def test_check_digest_with_values_csar():
    true_sha_and_values_csar = argparse.Namespace(sha512=True, manifest='', values_csar='aValuesCsar')
    assert generate.check_digest(true_sha_and_values_csar) == 'SHA-512'


def test_check_digest_without_manifest_and_values_csar():
    true_sha_only = argparse.Namespace(sha512=True, manifest='', values_csar='')
    assert generate.check_digest(true_sha_only) == ''


def test_check_digest_false_sha():
    true_sha_and_manifest = argparse.Namespace(sha512=False, manifest='')
    assert generate.check_digest(true_sha_and_manifest) == ''


expected_images = [
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-controller', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-certificate-mgr-agent', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-certificate-mgr', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-sidecar-injector', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-proxy', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-tools', tag='1.1.0-130'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-gs-service-mesh/eric-mesh-proxy-init', tag='1.1.0-130')]


def test_images_from_values_file():
    with open(os.path.join(RESOURCES, "values.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == len(expected_images)
    assert all(elem in expected_images for elem in image_list)


def test_images_from_values_file_no_global():
    with open(os.path.join(RESOURCES, "values_no_global.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_global_registry():
    with open(os.path.join(RESOURCES, "values_no_global_registry.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_global_registry_url():
    with open(os.path.join(RESOURCES, "values_no_global_registry_url.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_image_credentials():
    with open(os.path.join(RESOURCES, "values_no_image_credentials.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_repo_path():
    with open(os.path.join(RESOURCES, "values_no_repo_path.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_image_name():
    with open(os.path.join(RESOURCES, "values_no_name.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


def test_images_from_values_file_no_image_tag():
    with open(os.path.join(RESOURCES, "values_no_tag.yaml"), "r") as values:
        image_list = generate.__parse_values_file_for_images(values.read())
    assert len(image_list) == 0


yaml_parsing_expected_images = [
    Image(repo='armdocker.rnd.ericsson.se/proj-am/releases/eric-am-onboarding-service', tag='stable'),
    Image(repo='armdocker.rnd.ericsson.se/proj-am/releases/eric-am-common-wfs', tag='1.0.174-1'),
    Image(repo='armdocker.rnd.ericsson.se/proj-orchestration-so/bro-agent-fm', tag='bfh54fg4'),
    Image(repo='armdocker.rnd.ericsson.se/proj-am/sles/sles-pg10', tag='latest'),
    Image(repo='armdocker.rnd.ericsson.se/proj-orchestration-so/keycloak-client', tag='latest')]


def test_images_from_helm_template_valid_template():
    with open(os.path.join(RESOURCES, "helm_templates/valid_template.yaml"), "r") as helm_template:
        image_list = generate.__parse_images_from_template(helm_template.read())
    assert len(image_list) == 5
    assert all(elem in yaml_parsing_expected_images for elem in image_list)


def test_images_from_helm_template_with_duplicates():
    with open(os.path.join(RESOURCES, "helm_templates/valid_template_with_duplicate_images.yaml"),
              "r") as helm_template:
        image_list = generate.__parse_images_from_template(helm_template.read())
    assert len(image_list) == 5
    assert all(elem in yaml_parsing_expected_images for elem in image_list)


def test_images_in_scalar_values_check():
    with open(os.path.join(RESOURCES, "helm_templates/valid_template_with_images_in_scalars.yaml"),
              "r") as helm_template:
        assert generate.__images_in_scalar_values((helm_template.read())) is not None


def test_empty_images_section_generation():
    with TemporaryDirectory() as tempdir:
        os.makedirs(os.path.join(tempdir, "Files"))
        generate.empty_images_section(tempdir)
        count = 0
        for root, subdirs, files in os.walk(tempdir):
            for filename in files:
                count += 1
                assert filename == 'images.txt'
        assert count == 1


eric_product_info_expected_images = [
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-rs-storage-encr-released/eric-cs-storage-encryption-provider-plugin', tag='1.1.0-35'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-rs-storage-encr-released/eric-cs-storage-encryption-provider-mount', tag='1.1.0-35'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-rs-storage-encr-released/eric-cs-storage-encryption-provider-livenessprobe', tag='2.4.0-32'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-rs-storage-encr-released/eric-cs-storage-encryption-provider-node-driver-registrar', tag='2.3.0-34'),
    Image(repo='armdocker.rnd.ericsson.se/proj-adp-rs-storage-encr-released/eric-cs-storage-encryption-provider-external-provisioner', tag='3.0.0-41')
]


def test_parse_eric_product_info_for_images():
    with open(os.path.join(RESOURCES, "eric-product-info.yaml"), "r") as product_info:
        data = safe_load(product_info)
    images_list = generate.__parse_images_from_eric_product_info(data)
    assert len(images_list) == 5
    assert all(elem in eric_product_info_expected_images for elem in images_list)


def test_extract_crds():
    with TemporaryDirectory() as helmdir:
        with TemporaryDirectory() as outdir:
            generate_directory_structure(
                {
                    "eric-crd": {
                        "crd1-1.0.0.tgz": None,
                        "crd2-1.0.0.tgz": None
                    },
                    "charts": {
                        "subchart": {
                            "eric-crd": {
                                "subcrd-1.0.0.tgz": None,
                                "noversion.tgz": None,
                                "crd1-0.0.1.tgz": None
                            }
                        }
                    }
                },
                Path(helmdir)
            )
            extract_crds(Path(helmdir), Path(outdir))
            assert len(actual_list(outdir)) == len(expected_list(outdir)) and sorted(
                actual_list(outdir)) == sorted(expected_list(outdir))


def actual_list(outdir):
    return list(Path(outdir).rglob("*"))


def expected_list(outdir):
    return [Path(outdir, "crd1-1.0.0.tgz"),
            Path(outdir, "crd2-1.0.0.tgz"),
            Path(outdir, "subcrd-1.0.0.tgz")]
