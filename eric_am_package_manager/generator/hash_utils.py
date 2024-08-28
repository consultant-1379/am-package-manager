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
"""Hash utilities"""

import hashlib


def sha224(file_path):
    """Hash with SHA-224

    :param file_path: File to hash
    :return: Generated hash
    """
    hash_sha224 = hashlib.sha224()
    return hash_file(file_path, hash_sha224)


def sha256(file_path):
    """Hash with SHA-256

    :param file_path: File to hash
    :return: Generated hash
    """
    hash_sha256 = hashlib.sha256()
    return hash_file(file_path, hash_sha256)


def sha384(file_path):
    """Hash with SHA-384

    :param file_path: File to hash
    :return: Generated hash
    """
    hash_sha384 = hashlib.sha384()
    return hash_file(file_path, hash_sha384)


def sha512(file_path):
    """Hash with SHA-512

    :param file_path: File to hash
    :return: Generated hash
    """
    hash_sha512 = hashlib.sha512()
    return hash_file(file_path, hash_sha512)


def hash_file(file_path, hash_sha):
    """Hash file with given hash function

    :param file_path: File to hash
    :param hash_sha: HASH function
    :return: Generated hash
    """
    with open(file_path, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b''):
            hash_sha.update(chunk)
    return hash_sha.hexdigest()


# pylint: disable=unnecessary-lambda
HASH = {'sha-224': lambda file_path: sha224(file_path),
        'sha-256': lambda file_path: sha256(file_path),
        'sha-384': lambda file_path: sha384(file_path),
        'sha-512': lambda file_path: sha512(file_path)}
