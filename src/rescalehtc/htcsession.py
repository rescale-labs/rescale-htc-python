from __future__ import annotations

import requests
from .bearer_token import BearerToken
from .internals import authenticate, constants
from . import bearer_token
from .logger import logger
from datetime import datetime, timedelta
import random

class HtcSession:
    """
    Top level of rescalehtc, keeping the authentication
    state and allowing reauthentication as needed. This
    object needs to be passed into any function that will
    talk to the Rescale API.

    Before instancing this class for the first time in a non-rescale environment
    such as your own machine or a VM, use the ``rauthenticate`` executable script
    that comes bundled with rescalehtc. This writes tokens to ``~/.config/rescalehtc/`` for later use.

    In an interactive environment, do:

    ``> rauthenticate --interactive``

    This will prompt you for API key.

    If you're using this package in a non-interactive environment (e.g. in a container), you may do

    ``> rauthenticate``

    This will look for environment variables with either a ``RESCALE_HTC_REFRESH_TOKEN``
    or ``RESCALE_API_TOKEN``, which will be used to obtain the Bearer token used for
    later operations.
    """

    def __init__(self, workspace="default", config_folder_override=None):
        """
        :param workspace: Optional: If you are working with multiple workspaces (which each has their own API key), then specify the workspace name here. This is required if you have more than 1 API key in ~/.config/rescalehtc/.
        :param config_folder_override: Optional: Override the default configuration folder, which by default is ~/.config/.rescalehtc/.
        """

        self.workspace = workspace

        # Store these constants in the HtcSession object, to simplify mocking them during unittest
        self.RESCALE_API_BASE_URL = HtcSession.get_rescale_api_base_url()
        self.CONFIG_FOLDER = HtcSession.get_config_folder(config_folder_override)

        # Use a shared requests session
        self.requests_session = requests.Session()

        self.do_authenticate()

    # Perform authentication and set member variables
    def do_authenticate(self):
        self.bearer_json = authenticate.get_bearer_json(
            self.requests_session, self.workspace, self.CONFIG_FOLDER, self.RESCALE_API_BASE_URL
        )
        self.bearer_expiry = datetime.fromisoformat(self.bearer_json["expiresAt"])
        self.RESCALE_HTC_BEARER_TOKEN = self.bearer_json["tokenValue"]

    # Check if the bearer token has sufficient time left, and if not renew it
    def reauthenticate_if_needed(self):
        now = datetime.now()

        # Minimum time remaining is random between 2h and 2h20m, this reduces the odds
        # of write collisions for the bearer token.
        minimum_remaining_time = timedelta(hours=2, seconds=random.uniform(0, 20 * 60))

        if now + minimum_remaining_time > self.bearer_expiry:
            logger.debug("Reauthenticating check determined that bearer token should be renewed.")
            self.do_authenticate()

    def get_bearer_token(self) -> BearerToken:
        """
        Get a BearerToken object for the currently active Rescale HTC Bearer token,
        which is a JSON Web Token (JWT).

        The returned object enables easy access to the claims in the JWT.
        """
        self.reauthenticate_if_needed()
        return bearer_token.token_from_str(self.RESCALE_HTC_BEARER_TOKEN)

    # Function for getting the base API URL, this function is mocked during unittests
    def get_rescale_api_base_url():
        return constants._RESCALE_API_BASE_URL

    # Function for getting the config folder, this function is mocked during unittests
    def get_config_folder(config_folder_override):
        if config_folder_override:
            return config_folder_override
        else:
            return constants._CONFIG_FOLDER
