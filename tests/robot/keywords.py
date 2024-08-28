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
import hashlib
from hashlib import sha512
from robot.api.deco import keyword
from robot.api import logger
import os
import re
import subprocess



@keyword('Generate hash')
def generate_hash(directory):
    print(sha512(directory).hexdigest())
    return sha512(directory).hexdigest()


@keyword('Read csar')
def read_csar(csar_to_read):
    csar_hash_dict = {}
    for root, subFolders, files in os.walk(csar_to_read):
        for file_to_hash in files:
            if file_to_hash != 'acceptance.mf':
                filepath = os.path.join(root, file_to_hash)
                if not os.path.isdir(filepath):
                    with open(filepath, 'rb') as fp:
                        hash_of_file = _hash_value_for_file(fp, hashlib.new('SHA512'))
                        logger.debug(
                            "File: " + file_to_hash + " Hash:" + _hash_value_for_file(fp, hashlib.new('SHA512')))
                        csar_hash_dict[str(file_to_hash)] = hash_of_file
    for entry, val in list(csar_hash_dict.items()):
        print(entry + ": " + val)
    return csar_hash_dict


def _hash_value_for_file(f, hash_function, block_size=2 ** 20):
    while True:
        data = f.read(block_size)
        if not data:
            break
        hash_function.update(data)
    return hash_function.hexdigest()


@keyword('Create dict of files and hashes')
def create_dict_of_files_and_hashes(manifest_file):
    source_pattern = re.compile("(Source: .*)")
    hash_pattern = re.compile("(Hash: .*)")
    with open(manifest_file) as f:
        contents = f.read()
        source_result = source_pattern.findall(contents)
        hash_result = hash_pattern.findall(contents)
        file_hash_dict = {}
        for i in range(len(source_result)):
            source2 = os.path.basename(source_result[i])
            hash_of_file = str(hash_result[i]).partition(' ')[-1]
            file_hash_dict[source2] = hash_of_file
    for entry, val in list(file_hash_dict.items()):
        print(entry + ": " + val)
    return file_hash_dict


def compare_dicts(dict1, dict2):
    return (len(dict1) > len(dict2)) - (len(dict1) < len(dict2))


@keyword('Reading manifest for signature')
def reading_manifest_for_signature(manifest_file):
    with open(manifest_file) as f:
        signature = re.search("(?<=--BEGIN CMS-----\n)(.|\n|\S)*?(?=-----END CMS-----)", f.read(), re.MULTILINE)
        return signature.group(0)

@keyword('Run verification of signature')
def run_verification_of_signature(directory, datafile, signature, certfile, root_ca):
    try:
        exit_code = subprocess.check_call(["/usr/bin/openssl", "cms", "-binary", "-verify",
                               "-in", str(signature),
                               "-inform", "pem",
                               "-content", str(datafile),
                               "-CAfile", str(root_ca),
                               "-certfile", str(certfile),
                               "-out", str(directory) + "/output.txt"],
                              )
        return exit_code
    except Exception as ex:
        raise IOError('The process did not exit successfully. Exception is : ', ex)
