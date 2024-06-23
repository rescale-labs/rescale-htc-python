from __future__ import annotations
import os
import json
import datetime
import requests
import random
import threading

from ..internals.constants import REQUESTS_TIMEOUTS
from ..exceptions import HtcException
from ..logger import logger

# Functions which returns a Bearer token, wrapped in a dict
# Automatically refreshes the Bearer token if it does not have enough
# lifetime remaining, with either the API key or a refresh token.
# Writes new token to file afterwards.

semaphore = threading.Semaphore(1)


def get_bearer_json(
    requests_session: requests.Session,
    workspace: str,
    config_folder: str,
    rescale_api_base_url: str,
):
    workspace_config_folder = f"{config_folder}/{workspace}"

    token_file = f"{workspace_config_folder}/rescale_api_token.txt"

    if "RESCALE_HTC_REFRESH_TOKEN" in os.environ:
        logger.debug(
            f"Using RESCALE_HTC_REFRESH_TOKEN, not file {token_file}, for getting Bearer token."
        )
        if not os.path.isdir(workspace_config_folder):
            os.makedirs(workspace_config_folder)
        RESCALE_API_TOKEN = None
    else:
        if not os.path.isfile(token_file):
            msg = (
                f"Missing file {token_file} that should contain RESCALE_API_TOKEN, required for "
                + "using the Rescale HTC API. Run the 'rauthenticate' utility first."
            )
            logger.error(msg)
            raise HtcException(msg)

        logger.debug(f"Read API token from file {token_file}")
        logger.debug(f"Using authenticating against base URL {rescale_api_base_url}")
        with open(token_file) as fp:
            RESCALE_API_TOKEN = fp.read().strip()

    # Check for a bearer token with at least ~2 more hours of life left, otherwise request a new one
    bearer_token_file = f"{workspace_config_folder}/rescale_bearer_token.json"

    request_new_token = False
    if not os.path.isfile(bearer_token_file):
        logger.debug(f"No existing bearer token in {bearer_token_file}")
        request_new_token = True
    else:
        with open(bearer_token_file) as fp:
            bearer_json = json.load(fp)

            expiry_time = datetime.datetime.fromisoformat(bearer_json["expiresAt"])

            # Minimum time remaining is random between 2h and 2h20m, this reduces the odds
            # of write collisions for the bearer token.
            minimum_remaining_time = datetime.timedelta(
                hours=2, seconds=random.uniform(0, 20 * 60)
            )

            if datetime.datetime.now() + minimum_remaining_time > expiry_time:
                logger.debug(
                    f"Existing bearer token in {bearer_token_file} has expired (needed to be valid for at least {minimum_remaining_time} longer)"
                )
                request_new_token = True
            else:
                logger.debug(f"Reused existing bearer token from {bearer_token_file}")

    if request_new_token:
        # Get a new bearer token
        if "RESCALE_HTC_REFRESH_TOKEN" in os.environ:
            logger.debug(
                "Requesting bearer token from Rescale API, using RESCALE_HTC_REFRESH_TOKEN token"
            )
            bearer_token_res = requests_session.get(
                f"{rescale_api_base_url}/auth/token",
                headers={
                    "Authorization": f"Refresh {os.environ['RESCALE_HTC_REFRESH_TOKEN']}"
                },
                timeout=REQUESTS_TIMEOUTS,
            )
        else:
            logger.debug("Requesting bearer token from Rescale API, using API token")
            bearer_token_res = requests_session.get(
                f"{rescale_api_base_url}/auth/token",
                headers={"Authorization": f"Token {RESCALE_API_TOKEN}"},
                timeout=REQUESTS_TIMEOUTS,
            )

        if bearer_token_res.status_code >= 400:
            msg = f"""Failed to authenticate to Rescale, check your API key.
            {bearer_token_res.text}
            "HTTP {bearer_token_res.status_code}"""
            logger.error(msg)
            raise HtcException(msg)

        bearer_json = bearer_token_res.json()

        expires_at = datetime.datetime.now() + datetime.timedelta(
            seconds=bearer_json["expiresIn"]
        )
        bearer_json["expiresAt"] = expires_at.isoformat()

        # Aquire a semaphore to make this thread safe
        semaphore.acquire()
        logger.debug(f"Writing new bearer token to file {bearer_token_file}")
        with open(bearer_token_file, "w") as fp:
            fp.write(json.dumps(bearer_json))
        os.chmod(bearer_token_file, 0o600)
        semaphore.release()

    logger.debug("Authenticated OK.")

    return bearer_json
