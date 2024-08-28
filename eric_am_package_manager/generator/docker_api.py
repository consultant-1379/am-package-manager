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
"""Docker API"""

import os
import json
import logging
import hashlib
from base64 import b64decode
import requests

API_MANIFEST = 'https://{server}/v2/{path}/manifests/{version}'
API_BLOB = 'https://{server}/v2/{path}/blobs/{digest}'


class DockerApiError(Exception):
    """Docker API Exception"""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)


# pylint: disable=too-few-public-methods
class DockerConfig:
    """Docker configuration"""

    def __init__(self, config_path):
        self.config = self.parse_config(config_path)

    @staticmethod
    def parse_config(config_path):
        """Parse Docker configuration file

        :param config_path: Path to the Docker config directory
        :return: Docker configuration as dictionary
        """
        with open(os.path.join(config_path, 'config.json'), 'r', encoding='utf-8') as config_file:
            return json.loads(config_file.read())

    def get_credentials(self, server_url):
        """Get credentials tuple for a given server

        :param server_url: Server URK
        :raises KeyError: Failed to get credentials for the server
        :return: Credentials tuple for the given server
        """
        credentials = self.config['auths'].get(server_url)
        if not credentials:
            raise KeyError(f'Credentials for server {server_url} not found')
        return tuple(b64decode(credentials['auth']).decode().split(':'))


# pylint: disable=too-few-public-methods
class DockerApi:
    """Docker API v2 client"""

    def __init__(self, docker_config_path, timeout=600):
        self.docker_config = DockerConfig(docker_config_path)
        self.timeout = timeout

    @staticmethod
    def get_path_components(image_path):
        """Split image URL to components

        :param image_path: Full Docker image path
        :raises KeyError: Invalid Docker image URL
        :return: <server>, <path>, <version>
        """
        path_components = image_path.split('/')

        # Split image URL to separate variables e.g. <server>/<path>/<image>:<version>
        server = path_components[0]
        path, version = '/'.join(path_components[1:]).split(':')

        return server, path, version

    def get_image_manifest(self, image_path):
        """Get image manifest

        :param image_path: Docker image URL
        :raises DockerApiError: Failed to fetch data from server or data invalid
        :return: Docker image manifest as dictionary
        """
        try:
            response = self._request_manifest(image_path)
            return response.json()
        except json.decoder.JSONDecodeError as exc:
            error_message = f'Error parsing manifest for {image_path}'
            raise DockerApiError(response.status_code, error_message) from exc

    def get_manifest_hash(self, image_path):
        """
        Get the sha256sum for the image manifest

        :param image_path: Docker image URL
        :raises DockerApiError: Failed to fetch data from server
        :return: sha256sum of the request text body
        """
        response = self._request_manifest(image_path)
        return hashlib.sha256(response.text.encode('utf-8')).hexdigest()

    def _request_manifest(self, image_path):
        """
        Make request for image manifest, returning the successful request
        or raising a DockerAPIError

        :param image_path: Docker image URL
        :raises DockerAPIError: Failed to fetch data from server
        :return: request response
        """
        server, path, version = self.get_path_components(image_path)
        credentials = self.docker_config.get_credentials(server)
        try:
            response = requests.get(
                API_MANIFEST.format(server=server,
                                    path=path,
                                    version=version),
                auth=credentials,
                headers={
                    'Accept': 'application/vnd.docker.distribution.manifest.v2+json'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException,
                requests.exceptions.HTTPError) as exc:
            logging.debug('Could not get image manifest for %s (%s)', image_path, str(exc))
            error_message = f'Error requesting manifest: {str(exc)}'
            raise DockerApiError(response.status_code, error_message) from exc

    def get_blob(self, image_path):
        """Get image blob

        :param image_path: Full Docker image URL
        :raises DockerApiError: Failed to fetch data from server or data invalid
        :raises DockerApiError: Invalid data in response from the repository
        :return: Docker image blob dictionary
        """
        server, path, _ = self.get_path_components(image_path)
        credentials = self.docker_config.get_credentials(server)

        manifest = self.get_image_manifest(image_path)

        try:
            digest = manifest['config']['digest']
            media_type = manifest['config']['mediaType']
        except KeyError as exc:
            raise DockerApiError(200, f'Invalid data in image manifest {image_path}') from exc

        try:
            response = requests.get(API_BLOB.format(server=server, path=path, digest=digest),
                                    auth=credentials,
                                    headers={'Accept': media_type},
                                    timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logging.debug('Could not get labels for %s (%s)', image_path, exc)
            error_message = f'Failed to get image labels: {str(exc)}'
            raise DockerApiError(response.status_code, error_message) from exc
        except json.decoder.JSONDecodeError as exc:
            raise DockerApiError(response.status_code, 'Invalid data in image manifest') from exc

    def image_exists(self, image_path):
        """Check if Docker image exists in the repository

        :param image_path: Full Docker image URL
        :raises DockerApiError: On any other error except "not found"
        :return: True if image found from repository, else False
        """
        try:
            self.get_image_manifest(image_path)
            logging.debug('Image %s accessible in repository', image_path)
            return True
        except DockerApiError as exc:
            if exc.status_code == 404:
                return False
            raise

    def get_labels(self, image_path):
        """Return dictionary of labels for an image

        :param image_path: Full Docker image path
        :return: Image labels as dictionary, empty dictionary if not found
        """
        blob = self.get_blob(image_path)
        try:
            return blob['config']['Labels'] or {}
        except KeyError:
            return {}
