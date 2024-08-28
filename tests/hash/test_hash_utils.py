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
from eric_am_package_manager.generator import hash_utils
import pytest
import os

ROOT_DIR = os.path.abspath(os.path.join((os.path.abspath(__file__)), os.pardir))
RESOURCES = os.path.abspath(os.path.join(ROOT_DIR, os.pardir, 'resources'))


def test_sha256():
    assert hash_utils.HASH['sha-224'](RESOURCES + '/test_hash_dont_modify.tar') == 'a24a0030964d776dd949d3b68ef9a2e1840d9f65354c8ecd336fc977'


def test_sha384():
    assert hash_utils.HASH['sha-256'](RESOURCES + '/test_hash_dont_modify.tar') == '5ee9f51545d521add1c552f127bbee0085418dbc83a83db9f3391a145a9210d7'


def test_sha512():
    assert hash_utils.HASH['sha-384'](
        RESOURCES + '/test_hash_dont_modify.tar') == '28fb2470b3ae467318316ac3ae30b5b7f0e99e81326991f07fc37b74cc849626a70d7cff68e3c581cac1f6014c60b5fa'


def test_sha224():
    assert hash_utils.HASH['sha-512'](RESOURCES + '/test_hash_dont_modify.tar') == \
           '5946f73447d5165334d9f119a570fdf0092ee7d2fd3cfd945b563e6d05aeb1a8a61ab67da6406f4440611b39a8aa53de1434507e6942953d393c08aab8ff19b8'


def test_unknown_sha_key():
    with pytest.raises(KeyError) as output:
        hash_utils.HASH['md5'](RESOURCES + '/test_hash_dont_modify.tar')
