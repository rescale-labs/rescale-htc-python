"""
This file contains low-level API calls, matching the Rescale HTC API
exactly. Naming pattern for the functions is the HTTP method, followed
by the URL elements where / is replaced with _ and parameters are skipped.

E.g. POST /htc/projects/{projectId}/tasks/{taskId}/jobs/batch

Becomes: post_htc_projects_tasks_jobs_batch(...)

API calls that result in a HTTP 400 or larger code, for example due
to input error, will cause these functions to raise a HtcException.
"""

from __future__ import annotations
from typing import Optional

from . import HtcSession
from .internals.rest_helpers import api_get, api_post, api_put, api_patch, api_delete
from .exceptions import HtcException


# *********************
# Token Resource
# *********************


def get_well_known_jwks(rescale: HtcSession) -> dict:
    """
    Corresponds to API call:

    GET /.well-known/jwks.json

    This API call returns the Javascript Webtoken Key (JWK), used
    to check whether Bearer JWT tokens are correctly signed.
    """
    return api_get(rescale, f"{rescale.RESCALE_API_BASE_URL}/.well-known/jwks.json")


def get_auth_token(rescale: HtcSession, authorization_header: str) -> dict:
    """
    Corresponds to API call:

    GET /auth/token

    This endpoint should never be called, as the HtcSession object
    already contains a token to use.
    Call :func:`rescalehtc.htcsession.HtcSession.get_bearer_token`
    instead to get a valid Bearer token if you need one.

    This API call returns a rescale bearer token.

    You must provide an API key to this function, as this endpoint requires that type of key.
    Set the ``authorization_header`` to:

    Token <RESCALE_API_TOKEN>
    or
    Refresh <RESCALE_HTC_REFRESH_TOKEN>
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/auth/token",
        custom_auth_header=authorization_header,
    )


def get_auth_token_whoami(rescale: HtcSession) -> dict:
    """
    Corresponds to API call:

    GET /auth/token/whoami

    This API call returns the payload part of the Rescale Bearer token, which
    contains Rescale "Who Am I" information about the user. It uses the
    the Bearer token for authentication.
    """
    return api_get(rescale, f"{rescale.RESCALE_API_BASE_URL}/auth/token/whoami")


def get_auth_whoami(rescale: HtcSession, authorization_header: str) -> dict:
    """
    Corresponds to API call:

    GET /auth/whoami

    This API call returns Rescale "Who Am I" information about the user. When using
    this library, prefer using :func:`rescalehtc.api.get_auth_token_whoami` instead,
    which uses the more convenient Bearer token in HtcSession, and typically
    contains sufficient information.

    You must provide an API key to this function, as this endpoint requires that type of key.
    Set the ``authorization_header`` to:

    Token <RESCALE_API_TOKEN>
    or
    Refresh <RESCALE_HTC_REFRESH_TOKEN>
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/auth/whoami",
        custom_auth_header=authorization_header,
    )

def post_oauth_token(rescale: HtcSession) -> dict:
    """
    Corresponds to API call:

    POST /oauth2/token

    This API call is not implemented in this library yet and will return a NotImplementedError.
    """
    raise NotImplementedError("POST /oauth2/token not implemented in this library yet")

# *********************
# Provider Resource
# *********************


def get_htc_gcp_clusters(rescale: HtcSession, workspace_id: str) -> dict:
    """
    Corresponds to API call:

    GET /htc/gcp/clusters/{workspaceId}

    Get information about the GCP cluster. Unknown use.
    """
    return api_get(
        rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/gcp/clusters/{workspace_id}"
    )


def get_htc_regions(rescale: HtcSession, region: str = None) -> dict:
    """
    Corresponds to API call:

    GET /htc/regions

    GET /htc/regions/{region}

    Get the regions that are configured in thie workspace. If region is specified,
    get information about a specific region.
    """
    if region == None:
        return api_get(rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/regions")
    else:
        return api_get(rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/regions/{region}")


# *********************
# Metrics Resource
# *********************


def get_htc_metrics(rescale: HtcSession) -> dict:
    """
    THIS FUNCTION IS NOT IMPLEMENTED AND WILL RAISE AN EXCEPTION.

    Corresponds to API call:

    GET /htc/metrics

    This API call is used for metrics, it's not a normal REST endpoint.
    This function raises an exception.
    """
    raise HtcException("/htc/metrics is not a valid endpoint for REST")


# *********************
# Project Resource
# *********************


def get_htc_projects(rescale: HtcSession, project_id: str = None) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects

    GET /htc/projects/{projectId}

    Get all Rescale projects within a workspace. If providing a project_id,
    get the details for a single rescale project.
    """
    if project_id == None:
        return api_get(rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects")
    else:
        return api_get(
            rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}"
        )


def post_htc_projects(rescale: HtcSession, payload: dict) -> dict:
    """
    Corresponds to API call:

    POST /htc/projects/{projectId}

    Create a new HTC Project.
    """
    return api_post(
        rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects", payload=payload
    )

def get_htc_projects_dimensions(
    rescale: HtcSession, project_id: str) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/dimensions

    Retrieves the current set of dimension combinations configured for a specific project so that users can understand the existing computing environment constraints of a project.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/dimensions",
    )


def put_htc_projects_dimensions(
    rescale: HtcSession, project_id: str, payload: dict) -> dict:
    """
    Corresponds to API call:

    PUT /htc/projects/{projectId}/dimensions

    Create, update, or delete the dimension combinations for a project. For example, a project’s dimensions can be configured to require jobs to run on a particular type of processor architecture, within a certain region, and with or without hyperthreading.
    """
    return api_put(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/dimensions",
        payload=payload,
    )


def get_htc_projects_limits(
    rescale: HtcSession, project_id: str, id: Optional[int] = None
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/limits

    GET /htc/projects/{projectId}/limits/{id}

    Get resource limits for a specific project, like the vCPU limit.
    """
    if id == None:
        return api_get(
            rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits"
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits/{id}",
        )


def post_htc_projects_limits(
    rescale: HtcSession, project_id: str, payload: dict
) -> dict:
    """
    Corresponds to API call:

    POST /htc/projects/{projectId}/limits

    Set resource limits for a specific project, like the vCPU limit.
    """
    return api_post(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits",
        payload=payload,
    )


def delete_htc_projects_limits(rescale: HtcSession, project_id: str, id: Optional[int] = None) -> dict:
    """
    Corresponds to API call:

    DELETE /htc/projects/{projectId}/limits

    DELETE /htc/projects/{projectId}/limits/{id}

    Delete resource limits for a specific project, like the vCPU limit.
    """
    if id == None:
        return api_delete(
            rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits",
            return_json=False
        )
    else:
        return api_delete(
            rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits/{id}",
            return_json=False
        )


def patch_htc_projects_limits(
    rescale: HtcSession, project_id: str, id: int, payload: dict
) -> dict:
    """
    Corresponds to API call:

    PATCH /htc/projects/{projectId}/limits

    Set resource limits for a specific project, like the vCPU limit.
    """
    return api_patch(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/limits/{id}",
        payload=payload,
    )


def get_htc_projects_storage_presigned_url(
    rescale: HtcSession, project_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/storage/presigned-url

    Unknown use case.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/storage/presigned-url",
    )


def get_htc_projects_storage_token(
    rescale: HtcSession, project_id: str, region: str = None
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/storage/token

    GET /htc/projects/{projectId}/storage/token/{region}

    Get a token for the Rescale Object storage service, to be used to authenticate
    directly with the storage service (e.g. AWS S3 or Google Cloud Storage).
    """
    if region == None:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/storage/token",
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/storage/token/{region}",
        )


def get_htc_projects_storage_tokens(rescale: HtcSession, project_id: str) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/storage/tokens

    Get tokens for the Rescale Object storage service in all regions, to be used
    to authenticate directly with the storage service (e.g. AWS S3 or Google Cloud Storage).
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/storage/tokens",
    )


def get_htc_projects_task_retention_policy(rescale: HtcSession, project_id: str) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/task-retention-policy

    Retrieves the current task retention policy of a specific project. The task retention policy is necessary in managing the lifecycle of tasks within a project.

        Deletion Grace Period: The deleteAfter field represents the duration (in hours) after which an archived task is automatically deleted. Archived tasks can be unarchived during this period, protecting users from prematurely deleting task resources.

        Auto-Archive After Inactivity: The archiveAfter field represents the duration (in hours) of inactivity after which an active task is automatically archived. This feature helps in keeping the project organized by archiving active tasks, ensuring that storage resources are freed optimistically.

    Setting either value to 0 will result in disabling of that feature. For example, a project's task retention policy with deleteAfter set to 0 will result in tasks within that project never auto-deleting.

    If no policy is set at the project level (i.e., the response is a 404), the policy at the workspace level will apply. If the policy has archiveAfter or deleteAfter set to 0, it means that auto-archival or auto-deletion is disabled at the project level and any workspace level policy is ignored.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/task-retention-policy",
    )


def put_htc_projects_task_retention_policy(rescale: HtcSession, project_id: str, payload: dict) -> dict:
    """
    Corresponds to API call:

    PUT /htc/projects/{projectId}/task-retention-policy

    This endpoint enables project administrators to define or update the task retention policy for a specific project.
    """
    return api_put(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/task-retention-policy",
        payload
    )


def delete_htc_projects_task_retention_policy(rescale: HtcSession, project_id: str) -> dict:
    """
    Corresponds to API call:

    DELETE /htc/projects/{projectId}/task-retention-policy

    delete the task retention policy for the specified project. When a project-level policy is deleted, the auto-archival and auto-deletion behavior for tasks within the project will fall back to the workspace-level policy (if any). If no workspace-level policy is set, tasks within the project will not be subject to any auto-archival or auto-deletion.
    """
    return api_delete(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/task-retention-policy",
        return_json=False
    )


# *********************
# Container Registry Resource
# *********************


def get_htc_projects_container_registry_images(
    rescale: HtcSession, project_id: str, image_name: str = None
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/container-registry/images

    GET /htc/projects/{projectId}/container-registry/images/{imageName}

    Get list of all uploaded container images for a particular project. If image_name is specified,
    return information only about this image.
    """
    if image_name == None:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/container-registry/images",
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/container-registry/images/{image_name}",
        )


def post_htc_projects_container_registry_repo(
    rescale: HtcSession, project_id: str, repo_name: str
) -> dict:
    """
    Corresponds to API call:

    POST /htc/projects/{projectId}/container-registry/repo/{repoName}

    Create a container repository with the specified name for this project. This operation
    is idempotent, creating a new repository with an existing name does not overwrite or create
    a separate repository. There is no payload for this POST operation.
    """
    return api_post(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/container-registry/repo/{repo_name}",
        payload={},
    )


def get_htc_projects_container_registry_token(
    rescale: HtcSession, project_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/container-registry/token

    Get a token for authenticating against the container registry for this project. This
    token can be used for uploading/downloading container images with docker push/pull.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/container-registry/token",
        return_json=False,
    )


# *********************
# Task Resource
# *********************


def get_htc_projects_tasks(
    rescale: HtcSession, project_id: str, task_id: str = None
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks

    GET /htc/projects/{projectId}/tasks/{taskId}

    Get all Rescale projects within a project. A projectId must be provided.
    If providing a task_id, get the details for a single rescale task.
    """
    if task_id == None:
        return api_get(
            rescale, f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks"
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}",
        )


def post_htc_projects_tasks(
    rescale: HtcSession, project_id: str, payload: dict
) -> dict:
    """
    Corresponds to API Call:

    POST /htc/projects/{projectId}/tasks

    Create a new Rescale task under the specified project. Note that this
    is not idempotent: if you post tasks with the same name or description
    they will create a new unique task each time.
    """
    return api_post(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks",
        payload=payload,
    )


def delete_htc_projects_tasks(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API Call:

    DELETE /htc/projects/{projectId}/tasks/{taskId}

    Delete a rescale task. This frees the storage related to this task (after some time)
    and moves the task into state DELETED. The task itself in the API may not disappear
    immediately.
    """
    return api_delete(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}",
    )


def patch_htc_projects_tasks(
    rescale: HtcSession, project_id: str, task_id: str, payload: dict
) -> dict:
    """
    Corresponds to API Call:

    PATCH /htc/projects/{projectId}/tasks/{taskId}

    This endpoint allows for managing the lifecycle of tasks. To archive an active task, submit a PATCH request with "lifecycleStatus": "ARCHIVED".  To unarchive a task, PATCH it with "lifecycleStatus": "ACTIVE".
    """
    return api_patch(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}",
        payload=payload,
    )

def get_htc_projects_tasks_group_summary_statistics(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/group-summary-statistics

    Get a summary of all the jobs in a task, with their job statuses like RUNNING, SUCCEEDED etc.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/group-summary-statistics",
    )


def get_htc_projects_tasks_groups(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/groups

    Unknown use case. Returns a set of groups?
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/groups",
    )


def get_htc_projects_tasks_storage_presigned_url(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/storage/presigned-url

    Unknown use case.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/storage/presigned-url",
    )


def get_htc_projects_tasks_storage_regional_storage(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/storage/regional-storage

    Unknown use case.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/storage/regional-storage",
    )


def get_htc_projects_tasks_storage_token(
    rescale: HtcSession, project_id: str, task_id: str, region: str = None
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/storage/token

    GET /htc/projects/{projectId}/tasks/{taskId}/storage/token/{region}

    Get a token for the Rescale Object storage service, to be used to authenticate
    directly with the storage service (e.g. AWS S3 or Google Cloud Storage).
    """
    if region == None:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/storage/token",
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/storage/token/{region}",
        )


def get_htc_projects_tasks_storage_tokens(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/storage/tokens

    Get tokens for the Rescale Object storage service in all regions, to be used
    to authenticate directly with the storage service (e.g. AWS S3 or Google Cloud Storage).
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/storage/tokens",
    )


def get_htc_projects_tasks_summary_statistics(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API call:

    GET /htc/projects/{projectId}/tasks/{taskId}/summary-statistics

    Get a summary of all the jobs in a task, with their job statuses like RUNNING, SUCCEEDED etc.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/summary-statistics",
    )


# *********************
# Job Resource
# *********************


def get_htc_projects_tasks_jobs(
    rescale: HtcSession, project_id: str, task_id: str, job_id: str = None
) -> dict:
    """
    Corresponds to API Call:

    GET /htc/projects/{projectId}/tasks/{taskId}/jobs

    GET /htc/projects/{projectId}/tasks/{taskId}/jobs/{jobId}

    Get all jobs under a task. If a jobId is specified, return information about this
    specific job only.
    """
    if job_id == None:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs",
        )
    else:
        return api_get(
            rescale,
            f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs/{job_id}",
        )


def post_htc_projects_tasks_jobs_batch(
    rescale: HtcSession, project_id: str, task_id: str, payload: dict
) -> dict:
    """
    Corresponds to API Call:

    POST /htc/projects/{projectId}/tasks/{taskId}/jobs/batch

    Start a new rescale (batch) job. This runs the specified container as described in the
    payload on the rescale framework. The call returns information about the job batch.
    """
    return api_post(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs/batch",
        payload=payload,
    )


def post_htc_projects_tasks_jobs_cancel(
    rescale: HtcSession, project_id: str, task_id: str
) -> dict:
    """
    Corresponds to API Call:

    POST /htc/projects/{projectId}/tasks/{taskId}/jobs/cancel

    Cancel a submitted rescale job. This attemps to stop a running job or cancel a submitted one.
    There is no payload for this POST API call.
    """
    return api_post(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs/cancel",
        payload={},
        return_json=False,
    )


def get_htc_projects_tasks_jobs_logs(
    rescale: HtcSession, project_id: str, task_id: str, job_id: str, max_items : Optional[int] = None, page_size: int = 5000,
) -> dict:
    """
    Corresponds to API Call:

    GET /htc/projects/{projectId}/tasks/{taskId}/jobs/{jobId}/logs

    Get the stdout log for a particular rescale job that is or has been running.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs/{job_id}/logs",
        params={"pageSize": page_size},
        max_items = max_items
    )


def get_htc_projects_tasks_jobs_events(
    rescale: HtcSession, project_id: str, task_id: str, job_id: str
) -> dict:
    """
    Corresponds to API Call:

    GET /htc/projects/{projectId}/tasks/{taskId}/jobs/{jobId}/events

    Get a list of events for a particular rescale job that is or has been running.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/projects/{project_id}/tasks/{task_id}/jobs/{job_id}/events",
    )


# *********************
# Storage Resource
# *********************


def get_htc_storage(rescale: HtcSession) -> dict:
    """
    Corresponds to API Call:

    GET /htc/storage

    Get a basic information about the storage setup for this workspace.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/storage",
    )


def get_htc_storage_region(rescale: HtcSession, region: str) -> dict:
    """
    Corresponds to API Call:

    GET /htc/storage/region/{region}

    Get basic information about the storage setup for a region in this workspace.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/storage/region/{region}",
    )


# *********************
# Workspace Resource
# *********************

def get_htc_workspaces_dimensions(rescale: HtcSession, workspace_id: str) -> dict:
    """
    Corresponds to API Call:

    GET /htc/workspaces/{workspaceId}/dimensions

    Provides a comprehensive view of the various hardware configurations and environments available within a specific workspace.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/workspaces/{workspace_id}/dimensions",
    )


def get_htc_workspaces_limits(rescale: HtcSession, workspace_id: str) -> dict:
    """
    Corresponds to API Call:

    GET /htc/workspaces/{workspaceId}/limits

    Get resource limits for this workspace, like the vCPU limit.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/workspaces/{workspace_id}/limits",
    )


def get_htc_task_retention_policy(rescale: HtcSession, workspace_id: str) -> dict:
    """
    Corresponds to API Call:

    GET /htc/workspaces/{workspaceId}/task-retention-policy

    The task retention policy is necessary in managing the lifecycle of tasks within a Workspace. The task retention policy includes two key aspects:

        Deletion Grace Period: The deleteAfter field represents the duration (in hours) after which an archived task is automatically deleted. Archived tasks can be unarchived during this period, protecting users from prematurely deleting task resources.

        Auto-Archive After Inactivity: The archiveAfter field represents the duration (in hours) of inactivity after which an active task is automatically archived. This feature helps in keeping the project organized by archiving active tasks, ensuring that storage resources are freed optimistically.

    Setting either value to 0 will result in disabling of that feature. For example, a project's task retention policy with deleteAfter set to 0 will result in tasks within that project never auto-deleting.
    """
    return api_get(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/workspaces/{workspace_id}/task-retention-policy",
    )

def put_htc_task_retention_policy(rescale: HtcSession, workspace_id: str, payload: dict) -> dict:
    """
    Corresponds to API Call:

    GET /htc/workspaces/{workspaceId}/task-retention-policy

    The task retention policy is necessary in managing the lifecycle of tasks within a Workspace. The task retention policy includes two key aspects:
    """
    return api_put(
        rescale,
        f"{rescale.RESCALE_API_BASE_URL}/htc/workspaces/{workspace_id}/task-retention-policy",
        payload
    )
