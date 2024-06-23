#!/usr/bin/env python3


import argparse
import requests

from ..internals.constants import REQUESTS_TIMEOUTS
from .. import HtcSession, api
import logging
import os


def main(args):
    logger = logging.getLogger("RESCALEHTC")

    config_folder = HtcSession.get_config_folder(None)
    default_config_folder = f"{config_folder}/default"
    default_api_token_file = f"{default_config_folder}/rescale_api_token.txt"

    if args.interactive or "RESCALE_API_TOKEN" in os.environ:
        if args.interactive:
            print("Input your Rescale API key ( https://platform.rescale.com/user/settings/api-key/ ):")
            api_key = input()
        else:
            print("Using RESCALE_API_TOKEN env variable to authenticate to Rescale")
            api_key = os.environ["RESCALE_API_TOKEN"]

        # Attempt to use the API, and figure out which workspace it is related to
        endpoint = f"{HtcSession.get_rescale_api_base_url()}/auth/whoami"
        res = requests.get(
            endpoint,
            headers={"Authorization": f"Token {api_key}"},
            timeout=REQUESTS_TIMEOUTS,
        )
        if res.status_code >= 400:
            logger.error(
                "Error: Failed to authenticate with Rescale with the provided key:"
            )
            logger.error(res)
            logger.error(res.text)
            exit(1)

        # Extract the workspace name
        who_am_i = res.json()
        workspace_name = who_am_i["user"]["workspace"]["name"]

        print(
            f"API key belongs to Rescale workspace {workspace_name}, setting this as default workspace"
        )

        workspace_folder = f"{config_folder}/{workspace_name}"
        api_token_file = f"{workspace_folder}/rescale_api_token.txt"

        print(f"Writing API key to {api_token_file}")
        # Create the .rescalehtc folder
        if not os.path.isdir(config_folder):
            os.makedirs(config_folder)

        # Create the subfolder for the rescale workspace
        if not os.path.isdir(workspace_folder):
            os.makedirs(workspace_folder)

        # Remove any incorrect symlinks from default to workspace
        if (
            os.path.exists(default_config_folder)
            and os.readlink(default_config_folder) != workspace_folder
        ):
            os.remove(default_config_folder)

        # Add a symlink from .rescalehtc/default/ to .rescalehtc/<workspace>/
        if not os.path.exists(default_config_folder):
            os.symlink(
                workspace_folder, default_config_folder, target_is_directory=True
            )

        # Write the API token file
        with open(api_token_file, "w") as fp:
            fp.write(api_key)
        os.chmod(api_token_file, 0o600)

    elif os.path.isfile(default_api_token_file):
        print(
            f"File {default_api_token_file} with API token already exists, reusing that token."
        )

    elif "RESCALE_HTC_REFRESH_TOKEN" in os.environ:
        print("Using RESCALE_HTC_REFRESH_TOKEN env variable to refresh Bearer token")

    else:
        logger.error(
            "Error, neither --interactive specified nor RESCALE_API_TOKEN env variable set"
        )
        exit(1)

    print("Erasing any existing Bearer tokens")
    bearer_token_file = f"{default_config_folder}/rescale_bearer_token.json"
    if os.path.isfile(bearer_token_file):
        os.remove(bearer_token_file)

    print("Testing that authentation works:")

    rescale = HtcSession()

    whoami = api.get_auth_token_whoami(rescale)

    fullname = whoami['userFullName']
    email = whoami['userEmail']
    workspace = whoami['workspaceName']
    workspace_id = whoami['workspaceId']
    org = whoami['organizationCode']

    print(f"You are: {fullname} ({email}), in organization {org}, on workspace {workspace} ({workspace_id})")

    print("All OK.")


def argmain():
    parser = argparse.ArgumentParser(
        prog="Rescale Authentication Setup",
        description="Ineractive Command line utility for setting up your API key",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactively prompt for the API key. Otherwise looks for env variable RESCALE_API_TOKEN, or RESCALE_HTC_BEARER_TOKEN, or RESCALE_HTC_REFRESH_TOKEN.",
    )

    args = parser.parse_args()

    main(args)


if __name__ == "__main__":
    argmain()
