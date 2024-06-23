"""
This module deals with the container registry that belongs to a Rescale Project.
The container registry holds container images, that are later used by Rescale
to pull images to run.

Common use cases for this module is to fetch container registry authentication
tokens so that new images can be docker pushed to the registry. You can also
push docker images using functions on this object, create repositories, and
list/delete images from the registry.
"""

from __future__ import annotations
import json
from subprocess import run
import subprocess
import sys
from typing import Optional
from .htcprojects import HtcProject
from .exceptions import HtcException
from . import api
from .htcsession import HtcSession


class HtcContainerRegistry:
    """
    Class that holds information about a container registry. This info
    is commonly used to docker login, which enables docker push and
    docker pull of container images.

    Use the function :func:`rescalehtc.container_registry.get_container_registry`
    to create this object.

    The container registry token should be accessed through the
    :func:`rescalehtc.container_registry.HtcContainerRegistry.get_token` function,
    as keys may expire and require renewal (handled transparently by this class).
    """

    def __init__(self, project, registry_url, login_method, username, token):
        self.project: HtcProject = project
        self.registry_url: str = registry_url
        self.login_method: str = login_method
        self.username: str = username
        self._token: str = token

    def get_images(self, rescale: HtcSession) -> list[str]:
        """
        List all image names available in this container registry.
        """
        project_id = self.project.json["projectId"]
        images = api.get_htc_projects_container_registry_images(rescale, project_id)
        return images["images"]

    def push_docker_image(
        self,
        rescale: HtcSession,
        local_image_name: str,
        remote_image_name: Optional[str] = None,
        quiet: bool = False,
    ) -> str:
        """
        Helper function to push a local docker image to the remote Rescale container registry.
        The new remote docker image name is returned, use this name when submitting jobs later.

        The docker image must exist locally. If it is a remote image, run docker pull <imagename> first.

        This function invokes subprocess to run docker commands. It relies on `docker` being
        possible to run as the non-root user, described in https://docs.docker.com/engine/install/linux-postinstall/.

        Authentication towards the docker registry happens automatically. Repo creation is also
        handled automatically.

        By default, this function creates a unique remote image name. The name is uniquified
        with the image hash to avoid problems with reusing existing image tags and slow replication causing
        older images to be picked. To set your own remote image name, override the remote_image_name
        field.

        This function shows the stdout from the `docker` subprocess commands being run. To
        mute these, set quiet=True.
        """
        if "aws.com" not in self.registry_url:
            raise HtcException(
                f"Unable to push docker image to non-AWS registry {self.registry_url}, don't "
                "know how to authenticate against other registry types yet. Contact the maintainers."
            )

        if local_image_name.count(":") != 1:
            raise HtcException(
                f"A docker image name needs to be given with the full tag, in the format imagename:tag"
            )

        if quiet:
            stdout = subprocess.DEVNULL
        else:
            stdout = None

        if remote_image_name == None:
            # Get the current image ID/hash (not the digest). Use this
            # to uniquefy the remote image name.
            try:
                cmd = f"docker images --format json --no-trunc {local_image_name}"
                local_image_json_str = run(
                    cmd,
                    shell=True,
                    check=True,
                    capture_output=True,
                ).stdout.decode("utf-8")
            except Exception as e:
                raise HtcException(
                    f"Unable extract information about local docker image {local_image_name}. "
                    f"Can you run docker as this user? See https://docs.docker.com/engine/install/linux-postinstall/"
                    f" Error: {repr(e)}"
                )
            if local_image_json_str.strip() == "":
                raise HtcException(
                    f"Unable to find a local docker image named {local_image_name}. "
                    f"Does the image exist locally? If it is a remote image, you need to run "
                    f"'docker pull {local_image_name}' first. Command that was run: {cmd}")

            local_image_json = json.loads(local_image_json_str)
            # Pick out the sha256:b038788ddb222cb.... hash, then drop the sha prefix
            local_image_sha = local_image_json["ID"]
            if local_image_sha.count(":") != 1:
                raise HtcException(f"Got a weird docker image ID when running {cmd}: {local_image_json}")
            local_image_id = local_image_sha.split(':')[1]
            # Use the first 10 chars after : as the suffix for the container name
            remote_image_name = f"{local_image_name}-{local_image_id[:10]}"

        # Create the remote repo if it doesn't exist
        self.create_repo(rescale, remote_image_name.split(":")[0])

        try:
            # Log into the container registry
            cmd = f"echo {self.get_token(rescale)} | docker login {self.registry_url} --username {self.username} --password-stdin"
            run(
                cmd,
                shell=True,
                check=True,
                stderr=subprocess.STDOUT,
                stdout=stdout,
            )
        except Exception as e:
            raise HtcException(f"Unable to log into container registry: {repr(e)}")
        try:
            # Tag the image with the registry URL so that docker knows where to push it
            run(
                f"docker tag {local_image_name} {self.registry_url}{remote_image_name}",
                shell=True,
                check=True,
                stderr=subprocess.STDOUT,
                stdout=stdout,
            )
        except Exception as e:
            raise HtcException(
                f"Unable to tag docker image {local_image_name} as {self.registry_url}{remote_image_name}: {repr(e)}"
            )
        try:
            # Push the image to the cloud registry
            run(
                f"docker push {self.registry_url}{remote_image_name}",
                shell=True,
                check=True,
                stderr=subprocess.STDOUT,
                stdout=stdout,
            )
        except Exception as e:
            raise HtcException(
                f"Unable to push docker image to container registry: {repr(e)}"
            )

        # Empty the stdout buffer as we've used subprocess commands
        sys.stdout.flush()

        return remote_image_name

    def get_image(self, rescale: HtcSession, image_name: str) -> dict:
        """
        Show information about a container image with a specific name. Currently in the API
        this only returns a dict with 1 element: "status" : "PENDING" or "READY", indicating
        whether the image is ready for use or not.
        """
        return api.get_htc_projects_container_registry_images(
            rescale, self.project.json["projectId"], image_name
        )

    def is_image_ready(self, rescale: HtcSession, image_name: str) -> bool:
        """
        Returns true if the status of the container image is READY, otherwise false. An
        image in READY status can be used by rescale jobs.

        Use this function after pushing a new container image and before submitting jobs
        to Rescale. Attempting to start a job with an image in PENDING state causes a
        HtcException during job submission.

        Note that state READY does not guarantee you get the latest image, just that an
        image with this name is available in the repository.
        """
        return self.get_image(rescale, image_name)["status"] == "READY"

    def delete_image(self, rescale: HtcSession, image_name: str) -> bool:
        """
        Deletes an image from the container registry.
        """
        return api.delete_htc_projects_container_registry_images(
            rescale, self.project.json["projectId"], image_name
        )

    def get_repos(self, rescale: HtcSession) -> list[str]:
        """
        List all container repositories that have been created in this container registry.
        """
        project_id = self.project.json["projectId"]
        images = api.get_htc_projects(rescale, project_id)
        return images["repositories"]

    def create_repo(self, rescale: HtcSession, container_repo_name: str) -> dict:
        """
        Create a container image repo in this container registry with the specified name.
        """
        return api.post_htc_projects_container_registry_repo(
            rescale, self.project.json["projectId"], container_repo_name
        )

    def get_token(self, rescale: HtcSession) -> str:
        """
        Get a non-expired token for this container registry.

        TODO: Handle renewal of container registry tokens when they expire.
        For now this function just returns the token from when this
        object was created.
        """
        return self._token


def get_container_registry(
    rescale: HtcSession, project: HtcProject
) -> HtcContainerRegistry:
    """
    Get the container registry information needed to us it. This returns
    information such as the URL to the container registry, and the user
    name and password used to log into it.

    This function returns a HtcContainerRegistry object.
    """
    if not isinstance(project, HtcProject):
        raise HtcException(
            "Provided project argument is not a HtcProject object."
        )

    token = api.get_htc_projects_container_registry_token(
        rescale, project.json["projectId"]
    )
    registry_url = project.json["containerRegistry"]

    if "aws.com" in registry_url:
        username = "AWS"
        login_method = "username_token"
    else:
        raise HtcException(
            f"Unable to determine the type of container registry "
            f"for URL {registry_url}, needed to determine login method."
        )

    return HtcContainerRegistry(
        project, registry_url, login_method, username, token
    )
