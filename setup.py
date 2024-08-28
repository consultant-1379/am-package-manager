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
import os
from setuptools import find_packages, setup
import sys

if sys.version_info < (2, 7):
    sys.exit('AM Package Manager requires Python 2.7+')


root_dir = os.path.dirname(__file__)
install_requires = []
extras_require = {}

with open(os.path.join(root_dir, 'requirements.txt')) as requirements:
    for requirement in requirements.readlines():
        # get rid of comments or trailing comments
        requirement = requirement.split('#')[0].strip()
        if not requirement:
            continue # skip empty and comment lines
        # dependencies which use environment markers have to go in as
        # conditional dependencies under "extra_require", see more at:
        # https://wheel.readthedocs.io/en/latest/index.html#defining-conditional-dependencies
        if ';' in requirement:
            package, condition = requirement.split(';')
            cond_name = ':{0}'.format(condition.strip())
            extras_require.setdefault(cond_name, [])
            extras_require[cond_name].append(package.strip())
        else:
            install_requires.append(requirement)

setup(
    name='eric_am_package_manager',
    version=os.getenv('VERSION'),
    description='AM Package Manager',
    long_description="An internal tool to create CSAR files",
    license='Apache License Version 2.0',

    author='Ericsson',

    url='https://gerrit.ericsson.se/#/admin/projects/OSS/com.ericsson.orchestration.mgmt.packaging/am-package-manager',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration'],

    packages=find_packages(exclude=['tests*']),

    entry_points={
        'console_scripts': [
            'eric-am-package-manager = eric_am_package_manager.cli.__main__:main',
            'product-report = eric_am_package_manager.cli.product_report:main',]
    },

    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require)

