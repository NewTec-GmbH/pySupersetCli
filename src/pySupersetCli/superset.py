"""Server wrapper for requests to the Superset API."""

# BSD 3-Clause License
#
# Copyright (c) 2024 - 2025, NewTec GmbH
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICU5LAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

################################################################################
# Imports
################################################################################

from dataclasses import dataclass
import logging
import requests
import urllib3


################################################################################
# Variables
################################################################################

LOG: logging.Logger = logging.getLogger(__name__)

################################################################################
# Classes
################################################################################


class Superset:  # pylint: disable=too-few-public-methods
    """
    Wrapper of the requests module for the Superset API.
    Handles the authentication and the API calls.
    Implements parts of the Superset API: https://superset.apache.org/docs/api/
    """

    @dataclass
    class Provider:
        """
        Enum for the supported authentication providers.
        """
        DB = "db"
        LDAP = "ldap"

    # pylint: disable=too-many-arguments
    def __init__(self,
                 server_url: str,
                 username: str,
                 password: str,
                 provider: Provider,
                 verify_ssl: bool = True) -> None:
        """
        Initializes the Superset object and logs in the user.

        Args:
            server_url (str): The URL of the Superset server.
            username (str): The username of the user.
            password (str): The password of the user.
            provider (Provider): The authentication provider.
            verify_ssl (bool): Verify the SSL certificate of the server.
        """
        self._server_url: str = f"{server_url}/api/v1"
        self._access_token: str = ""
        self._csrf_token: str = ""
        self._cookies: dict = {}
        self._timeout: int = 60
        self._verify_ssl: bool = verify_ssl

        if not self._verify_ssl:
            # Disable SSL warnings if SSL verification is disabled
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Login the user and retrieve the access token and the CSRF token
        self._login(username, password, provider)

    def _login(self, username: str, password: str, provider: Provider) -> None:
        """
        Logs in the user and retrieves the access token and the refresh token.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
            provider (Provider): The authentication provider.

        Returns:
            None
        """
        login_endpoint: str = "/security/login"
        crsf_token_endpoint: str = "/security/csrf_token/"

        login_body: dict = {
            "password": password,
            "provider": provider,
            "refresh": True,
            "username": username
        }

        # Send the login request
        ret_code, response = self.request("POST",
                                          login_endpoint,
                                          json=login_body)

        if requests.codes.ok != ret_code:  # pylint: disable=no-member
            LOG.fatal("Login failed: %s", response.get("message"))
            raise RuntimeError("Login failed")

        self._access_token = response.get("access_token", "")

        # Get the CSRF token
        ret_code, response = self.request("GET", crsf_token_endpoint)

        if requests.codes.ok != ret_code:  # pylint: disable=no-member
            LOG.fatal("Get CSRF token failed: %s", response.get("message"))
            raise RuntimeError("Get CSRF token failed")

        self._csrf_token = response.get("result", "")

        if self._access_token == "" or self._csrf_token == "":
            LOG.fatal("Tokens failed: Access token or CSRF token not received.")
            raise RuntimeError("Tokens failed")

    def request(self,
                method: str,
                endpoint: str,
                **request_kwargs) -> tuple[int, dict]:
        """
        Sends a request to the Superset API.

        Args:
            method (str): The HTTP method of the request.
            endpoint (str): The endpoint of the request after '/api/v1'.
            data (dict): The data of the request.
            request_kwargs (dict): Additional keyword arguments for the request. 
                    Can be any accepted by the Requests module.

        Returns:
            tuple[int, dict]: The response code and the response data.
        """

        url: str = f"{self._server_url}{endpoint}"
        headers: dict = {}
        response_code: int = 0
        reponse_data: dict = {}

        # If already logged in, add the access token to the headers
        if self._access_token != "":
            headers = {
                'Authorization': f'Bearer {self._access_token}',
                'referer': self._server_url,
                'X-CSRFToken': self._csrf_token
            }

        try:
            # Send the request
            response: requests.Response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self._timeout,
                verify=self._verify_ssl,
                cookies=self._cookies,
                allow_redirects=False,
                ** request_kwargs)

            response_code = response.status_code
            reponse_data = response.json()

            if response.cookies:
                self._cookies = response.cookies.get_dict()

            LOG.info("Request: %s %s", method, url)
            LOG.info("Response Code: %s", response_code)

            # Check if the token has expired
            if (requests.codes.unauthorized == response_code) and \
                    (reponse_data.get('message') == "Token has expired"):  # pylint: disable=no-member
                LOG.error("Refreshing token is not implemented.")

        except requests.exceptions.JSONDecodeError as e:
            LOG.error("JSON decode error: %s", e)

        except requests.exceptions.Timeout as e:
            LOG.error("Timeout error: %s", e)

        except requests.exceptions.SSLError as e:
            LOG.error("SSL error: %s", e)
            if self._verify_ssl is True:
                LOG.error("If you trust the server you are connecting to (%s), " +
                          "consider deactivating SSL verification.", self._server_url)

        except requests.exceptions.RequestException as e:
            LOG.error("Request error: %s", e)

        return (response_code, reponse_data)


################################################################################
# Functions
################################################################################

################################################################################
# Main
################################################################################
