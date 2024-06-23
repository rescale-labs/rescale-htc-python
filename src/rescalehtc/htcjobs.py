"""
This module deals with Rescale Jobs and Batch Jobs, which
are where actual compute is performed in Rescale.
Jobs are returned as a HtcJob or HtcJobBatch objects.
"""
from __future__ import annotations
from datetime import datetime, timedelta
import logging
import tempfile
import time
import os
from typing import Iterable, Optional

from .internals.constants import (
    FLOOD_PREVENTION_INTERVAL_SECONDS,
    MAX_WAIT_FOR_IMAGE_TRANSITION_PENDING_READY_SECONDS,
)
from .exceptions import HtcException
from .htctasks import HtcTask
from . import HtcSession, api

logger = logging.getLogger("RESCALEHTC")


class HtcJob:
    """
    Class for a single Rescale Job.
    """

    def __init__(self, json: dict, task: HtcTask):
        now = datetime.now()
        self.json = json
        """The raw dictionary describing this Job. The dictionary follows the
        HTCJob schema in the Rescale HTC API documentation. Example contents:

        .. code-block:: json

            {
                "jobUUID": "155f18d4",
                "providerJobId": "provider-id-12345",
                "region": "AWS_AP_SOUTHEAST_1",
                "taskId": "task-12345",
                "projectId": "project-12345",
                "status": "FAILED",
                "statusReason": "Completed",
                "container": {
                    "exitCode": 3,
                    "reason": "Container Exited"
                },
                "createdAt": "2023-10-19T08:05:53.730Z",
                "createdBy": "qWoUF",
                "failureCode": "ErrorTimeout",
                "workspaceId": "04-8098234",
                "group": "sample-group",
                "commands": [
                    "python",
                    "script.py"
                ],
                "envs": [
                    {
                    "name": "FOO",
                    "value": "bar"
                    }
                ],
                "jobExecutionEnvironment": {
                    "instanceId": "123456789",
                    "instanceType": "c7g.medium",
                    "architecture": 2
                },
                "tags": [
                    {
                    "key": "HOME",
                    "value": "/home/users/"
                    }
                ],
                "architecture": "A100",
                "maxVCpus": 0,
                "maxMemory": 0,
                "maxDiskGiB": 0,
                "maxSwap": 0,
                "imageName": "string",
                "execTimeoutSeconds": 0,
                "updatedAt": "2023-10-19T08:05:53.730Z",
                "instanceLabels": {
                    "csp": "string",
                    "priority": "string",
                    "instanceType": "string",
                    "instanceArchitecture": "string",
                    "accountId": "string",
                    "region": "string"
                },
                "startedAt": "2023-10-19T08:05:53.730Z",
                "completedAt": "2023-10-19T08:05:53.730Z"
            }

        Access this member variable to extract information about a job.

        If this HtcJob object was created from a :func:`rescalehtc.htcjobs.HtcJobBatch.to_jobs`
        (which is common), then not all fields in the schema may be available. Only fields
        shared between all jobs and returned by the /htc/projects/{projectId}/tasks/{taskId}/jobs/batch
        endpoint would be available. Running :func:`rescalehtc.htcjobs.HtcJob.get_update` on this
        object would make all fields from /htc/projects/{projectId}/tasks/{taskId}/jobs/{jobId}
        available, but this should be used very rarely, especially with large number of jobs.
        """

        self.task = task
        self.status_updated_at = now - timedelta(hours=1)
        self.log_lines_updated_at = now - timedelta(hours=1)
        self.log_lines_raw_inverted = None

    def __repr__(self):
        return "HtcJob(" + str(self.json) + ")"

    # Refresh the information about a job
    def get_update(self, rescale: HtcSession) -> dict:
        """
        Update the job status for this job, getting the latest status. Returns the
        :attr:`rescalehtc.htcjobs.HtcJob.json` dict after updating.

        This function has basic flood prevention on the job status requests.
        The API never updates more than every 30 seconds anyway,
        so calling this function more often than that has no effect.
        """
        now = datetime.now()
        time_since_last_update = now - self.status_updated_at
        if time_since_last_update > timedelta(
            seconds=FLOOD_PREVENTION_INTERVAL_SECONDS
        ):
            logger.debug(f"Updated Rescale Job status, job id {self.json['jobUUID']}")
            self.json = api.get_htc_projects_tasks_jobs(
                rescale,
                project_id=self.json["projectId"],
                task_id=self.json["taskId"],
                job_id=self.json["jobUUID"],
            )
            self.status_updated_at = datetime.now()

            # Perform sanity check on the status field. We rely heavily on the potential values
            # not changing here, so we want to raise an exception if we encounter something
            # unexpected
            if self.json["status"] not in [
                "FAILED",
                "POD_FAILED",
                "POD_SUCCEEDED",
                "SUCCEEDED",
                "SUBMITTED_TO_RESCALE",
                "SUBMITTED_TO_PROVIDER",
                "RUNNABLE",
                "STARTING",
                "RUNNING",
            ]:
                raise HtcException(
                    "Updating a HtcJob status returned a status value that is not supported "
                    f"by this library: {self.json['status']}. "
                    "Please contact the library developers this is a critical bug in the library."
                )
        else:
            logger.debug(
                f"Skipped updating job status since last request was {time_since_last_update} ago, less than {FLOOD_PREVENTION_INTERVAL_SECONDS} seconds, jobId {self.json['jobUUID']}"
            )

        return self.json

    def is_still_running(self, rescale: HtcSession) -> bool:
        """
        Update the status of the job, and return true if the job is still running or pending.

        The possible values of the status field in :attr:`rescalehtc.htcjobs.HtcJob.json` are:

        ::

            Values indicating the job is no longer running
            ["FAILED", "POD_FAILED", "POD_SUCCEEDED", "SUCCEEDED"]

            Values indicating the job is still running
            ["SUBMITTED_TO_RESCALE", "SUBMITTED_TO_PROVIDER", "RUNNABLE", "STARTING", "RUNNING"]

        This function calls :func:`rescalehtc.htcjobs.HtcJob.get_update` and checks whether
        the status field is in the categories shown above.

        This function has basic flood prevention on the job status requests.
        The API never updates more than every 30 seconds anyway,
        so calling this function more often than that has no effect.
        """
        return self.get_update(rescale)["status"] in [
            "SUBMITTED_TO_RESCALE",
            "SUBMITTED_TO_PROVIDER",
            "RUNNABLE",
            "STARTING",
            "RUNNING",
        ]

    def get_logs(
        self, rescale: HtcSession, last_n_lines: Optional[int] = None
    ) -> Iterable[str]:
        """
        Get stdout logs for this job. Returns an iterator of strings, one per line.

        :param last_n_lines: Optional: The number of lines from the tail of the log to fetch, or None to get the entire log. Fewer log lines will fetch faster.

        The entire log is kept in memory, as the log from Rescale is fetched
        with the most recent line first, then reversed by this function into
        the normal reading order (oldest line first). This function may therefore
        consume a lot of memory.

        For a more memory efficient way of fetching a lot, consider using
        :func:`rescalehtc.htcjobs.HtcJob.get_logs_to_file`.

        This function has basic flood prevention on the job log requests.
        The API never updates more than every 30 seconds anyway,
        so calling this function more often than that has no effect.
        """
        now = datetime.now()

        time_since_last_update = now - self.log_lines_updated_at
        if self.log_lines_raw_inverted == None or time_since_last_update > timedelta(
            seconds=FLOOD_PREVENTION_INTERVAL_SECONDS
        ):
            logger.debug(f"Updated Rescale Logs, job id {self.json['jobUUID']}")
            logs_messages = api.get_htc_projects_tasks_jobs_logs(
                rescale,
                project_id=self.json["projectId"],
                task_id=self.json["taskId"],
                job_id=self.json["jobUUID"],
                max_items=last_n_lines,
            )
            self.log_lines_updated_at = datetime.now()
            self.log_lines_raw_inverted = [line["message"] for line in logs_messages]
        else:
            logger.debug(
                f"Skipped updating job logs since last request was {time_since_last_update} ago, less than {FLOOD_PREVENTION_INTERVAL_SECONDS} seconds, jobId {self.json['jobUUID']}"
            )

        return reversed(self.log_lines_raw_inverted)

    def get_logs_to_file(
        self,
        rescale: HtcSession,
        destination_file_path: str,
        last_n_lines: Optional[int] = None,
    ):
        """
        Get stdout logs for this job and write them to a file.

        :param last_n_lines: Optional: The number of lines from the tail of the log to fetch, or None to get the entire log. Fewer log lines will fetch faster.

        This function writes to a temporary file first, in the newest-line-first
        order that Rescale API returns logs. Then the log is reversed into the
        more friendly oldest line first ordering, and written to the target file.

        More memory efficient than :func:`rescalehtc.htcjobs.HtcJob.get_logs`,
        as the whole log is not kept in memory during fetching.
        """

        # Open a temporary file to write the reversed log file to
        with tempfile.TemporaryFile("wb+") as temp_fp:
            logs_messages = api.get_htc_projects_tasks_jobs_logs(
                rescale,
                project_id=self.json["projectId"],
                task_id=self.json["taskId"],
                job_id=self.json["jobUUID"],
                max_items=last_n_lines,
            )
            for line in logs_messages:
                temp_fp.write((line["message"] + "\n").encode())

            # Open the target file, write the lines in the correct order
            with open(destination_file_path, "w") as target_fp:
                for line in reverse_readline(temp_fp):
                    target_fp.write(line + "\n")


class HtcJobBatch:
    """
    Class for a batch series of rescale jobs.
    """

    def __init__(self, json: dict, task: HtcTask):
        self.json: dict = json
        """The raw dictionary describing a batch run of jobs. The dictionary
        follows the HTCJobSubmitRequest schema in the Rescale HTC API documentation.
        Example contents:

        .. code-block:: json

            [
                {
                    "jobName": "Sample job",
                    "taskId": "task-12345",
                    "projectId": "project-12345",
                    "parentJobId": "job-12345",
                    "createdBy": "qWoUF",
                    "workspaceId": "04-8234074",
                    "group": "sample-group",
                    "batchSize": 10,
                    "regions": [
                    "AWS_AP_SOUTHEAST_1"
                    ],
                    "rescaleTimeReceived": "2023-10-24T20:34:51.279Z",
                    "htcJobDefinition": {
                    "imageName": "my-image",
                    "maxVCpus": 8,
                    "maxMemory": 128,
                    "maxDiskGiB": 1,
                    "maxSwap": 0,
                    "tags": {
                        "HOME": "foo_bar"
                    },
                    "commands": [
                        "python",
                        "script.py"
                    ],
                    "envs": [
                        {
                        "name": "FOO",
                        "value": "bar"
                        }
                    ],
                    "claims": [
                        {
                        "name": "string",
                        "value": "string"
                        }
                    ],
                    "execTimeoutSeconds": 300,
                    "architecture": "A100",
                    "priority": "ON_DEMAND_ECONOMY"
                    },
                    "tags": [
                    {
                        "key": "HOME",
                        "value": "/home/users/"
                    }
                    ],
                    "jobDefinitionName": "job-definition-321",
                    "cloudProvider": "AWS"
                }
            ]

        Access this member variable to extract information about a batch of jobs.

        The dictionary contains the information given to the create_*_job* functions
        in this package.
        """
        self.task = task

    def __repr__(self):
        return "HtcJobBatch(" + str(self.json) + ")"

    def get_task_summary(self, rescale: HtcSession) -> dict:
        """
        Gets the task summary for the task of this HtcJobBatch.

        Note that this includes all jobs in the task, not just this HtcJobBatch.

        See documentation in :func:`rescalehtc.htctasks.HtcTask.get_task_summary`
        """
        return self.task.get_task_summary(rescale)

    def is_still_running(self, rescale: HtcSession) -> bool:
        """
        Check whether any jobs in the task for this HtcJobBatch are still running.

        Note that this includes all jobs in the task, not just this HtcJobBatch.

        See documentation in :func:`rescalehtc.htctasks.HtcTask.is_still_running`
        """
        return self.task.is_still_running(rescale)

    def to_jobs(self) -> list[HtcJob]:
        """
        Converts a HtcJobBatch to an iterator of HtcJob.
        The details of each HtcJob is a bit sparse, as we have not
        queried the API for the status of each individual job.

        The following fields are available without calling job.get_update():

        group, projectId, taskId, jobUUID

        If you want to monitor the status of a set of jobs, its more
        efficient to call :func:`~rescalehtc.htctasks.HtcTask.get_task_summary`
        on the task instead of polling the individual HtcJobs.
        """
        return [
            HtcJob(
                {
                    "group": self.json["group"],
                    "projectId": self.json["projectId"],
                    "taskId": self.json["taskId"],
                    "jobUUID": f'{self.json["parentJobId"]}:{i}',
                },
                self.task,
            )
            for i in range(self.json["batchSize"])
        ]


def get_jobs(
    rescale: HtcSession, task: HtcTask, job_status: str = "any"
) -> list[HtcJob]:
    """
    Get all jobs within a task with a particular job status. By default shows
    jobs with any status. Set job_status field e.g. to SUCCEEDED to filter on
    specific job statuses.
    """
    if isinstance(task, HtcTask):
        task_id = task.json["taskId"]
    else:
        raise HtcException("Provided argument task is not a HtcTask object.")

    any_job_status = True if job_status in ["any", "all", None] else False

    project_id = task.json["projectId"]

    all_jobs = api.get_htc_projects_tasks_jobs(rescale, project_id, task_id)
    matching_jobs = [
        HtcJob(job, task)
        for job in all_jobs
        if any_job_status or job["status"] == job_status
    ]
    return matching_jobs


def get_job_with_id(
    rescale: HtcSession, task: HtcTask, job_id: str
) -> HtcJob:
    """
    Get a job with a specific ID within a task.
    """
    if isinstance(task, HtcTask):
        task_id = task.json["taskId"]
    else:
        raise HtcException("Provided argument task is not a HtcTask object.")

    project_id = task.json["projectId"]
    task_id = task.json["taskId"]

    try:
        job = api.get_htc_projects_tasks_jobs(rescale, project_id, task_id, job_id)
    except HtcException as e:
        return None

    return HtcJob(job, task)


def create_single_job(
    rescale: HtcSession,
    task: HtcTask,
    priority: str,
    image_name: str,
    exec_timeout_seconds: int,
    job_name: str = "rescalehtc_default_jobname",
    max_vcpus: int = 1,
    max_memory_mib: int = 4000,
    max_swap_mib: int = 0,
    max_disk_gib: int = 10,
    job_tags: dict = {},
    batch_tags: list = [],
    commands: list = [],
    envs: list = [],
    claims: list = [],
    architecture: str = "AARCH64",
    region: str = None,
) -> HtcJob:
    """
    This function creates a single Rescale job. Inputs are split into python
    arguments, with many arguments having default values.

    This function returns a HtcJob.

    If you need to run several jobs, use :func:`create_job_batch` function instead.

    :param batch_size: The number of instances of this job to run
    :param priority: Job priority, one of [ON_DEMAND_ECONOMY, ON_DEMAND_PRIORITY]
    :param image_name: The container image name in the Rescale container registry to run
    :param exec_timeout_seconds: Number of seconds this container can execute for until it is stopped by timeout
    :param job_name: Optional: The name of the job batch
    :param max_vcpus: Optional: Number of vCPUs allocated to this container
    :param max_memory_mib: Optional: Maximum RAM usage for this container, in MiB
    :param max_swap_mib: Optional: Maximum Swap usage for this container, in MiB
    :param max_disk_gib: Optional: Maximum disk usage for this container, in GiB
    :param job_tags: Optional: Tags given to each job in a batch
    :param batch_tags: Optional: Tags given to the job batch
    :param commands: Optional: The command to run in the container, in list form: ['bash', '-c', 'echo hello world']
    :param envs: A list of environment variables to use in the run, as a list of dicts: [{"name": "MY_ENV_VAR", "value": "value_of_my_env_var"},..]
    :param claims: Optional: Custom JWT Claims that will be attached to the Rescale JWT Bearer Token, as a list of dicts: [{"name": "my_claim_name", "value": "my_claim_value"},..] . Note that the name given here is prefixed by userDefined\_ in the actual JWT. Use :func:`rescalehtc.bearer_token.BearerToken.get_user_claims` to retrieve custom claims easily.
    :param architecture: Optional: The architecture to run container on, one of [ AARCH64, A100, X86 ]
    :param region: Optional: The compute region to run the container in. If the Rescale Project only has a single region this value can remain as None, and the available region will be picked.

    If you need more control over the job definition than this function allows,
    then use the :func:`create_job_batch_raw` function instead.
    """
    batch = create_job_batch(
        rescale=rescale,
        task=task,
        batch_size=1,
        priority=priority,
        image_name=image_name,
        exec_timeout_seconds=exec_timeout_seconds,
        job_name=job_name,
        max_vcpus=max_vcpus,
        max_memory_mib=max_memory_mib,
        max_swap_mib=max_swap_mib,
        max_disk_gib=max_disk_gib,
        job_tags=job_tags,
        batch_tags=batch_tags,
        commands=commands,
        envs=envs,
        claims=claims,
        architecture=architecture,
        region=region,
    )
    parent_job_id = batch.json["parentJobId"]
    job_id = parent_job_id + ":0"

    return HtcJob(
        api.get_htc_projects_tasks_jobs(
            rescale, task.json["projectId"], task.json["taskId"], job_id
        ),
        task,
    )


def create_job_batch(
    rescale: HtcSession,
    task: HtcTask,
    batch_size: int,
    priority: str,
    image_name: str,
    exec_timeout_seconds: int,
    job_name: str = "rescalehtc_default_jobname",
    max_vcpus: int = 1,
    max_memory_mib: int = 4000,
    max_swap_mib: int = 0,
    max_disk_gib: int = 10,
    job_tags: dict = {},
    batch_tags: list = [],
    commands: list = [],
    envs: list = [],
    claims: list = [],
    architecture: str = "AARCH64",
    region: str = None,
) -> HtcJobBatch:
    """
    This function creates batch of Rescale jobs. Inputs are split into python
    arguments, with many arguments having default values.

    :param batch_size: The number of instances of this job to run
    :param priority: Job priority, one of [ON_DEMAND_ECONOMY, ON_DEMAND_PRIORITY]
    :param image_name: The container image name in the Rescale container registry to run
    :param exec_timeout_seconds: Number of seconds this container can execute for until it is stopped by timeout
    :param job_name: Optional: The name of the job batch
    :param max_vcpus: Optional: Number of vCPUs allocated to this container
    :param max_memory_mib: Optional: Maximum RAM usage for this container, in MiB
    :param max_swap_mib: Optional: Maximum Swap usage for this container, in MiB
    :param max_disk_gib: Optional: Maximum disk usage for this container, in GiB
    :param job_tags: Optional: Tags given to each job in a batch
    :param batch_tags: Optional: Tags given to the job batch
    :param commands: Optional: The command to run in the container, in list form: ['bash', '-c', 'echo hello world']
    :param envs: A list of environment variables to use in the run, as a list of dicts: [{"name": "MY_ENV_VAR", "value": "value_of_my_env_var"},..]
    :param claims: Optional: Custom JWT Claims that will be attached to the Rescale JWT Bearer Token, as a list of dicts: [{"name": "my_claim_name", "value": "my_claim_value"},..] . Note that the name given here is prefixed by userDefined\_ in the actual JWT. Use :func:`rescalehtc.bearer_token.BearerToken.get_user_claims` to retrieve custom claims easily.
    :param architecture: Optional: The architecture to run container on, one of [ AARCH64, A100, X86 ]
    :param region: Optional: The compute region to run the container in. If the Rescale Project only has a single region this value can remain as None, and the available region will be picked.

    If you need more control over the job definition than this function allows,
    then use the :func:`create_job_batch_raw` function instead.
    """
    if region == None:
        if len(task.project.json["regions"]) != 1:
            raise HtcException(
                f"During job creation, region argument was not given (None) but multiple regions "
                f"exist in this Rescale Project: {task.project.json['regions']}. If there are multiple "
                "regions, you need to explicitly pick one."
            )
        selected_region = task.project.json["regions"][0]
    else:
        selected_region = region

        if selected_region not in task.project.json["regions"]:
            raise HtcException(
                f"During job creation, region argument was set to {region} but this "
                f"region was not found in the Rescale Project: {task.project.json['regions']}"
            )

    if "GCP" in selected_region:
        cloud_provider = "GCP"
    elif "AWS" in selected_region:
        cloud_provider = "AWS"
    else:
        raise HtcException(
            f'Picked first region in {task.project.json["regions"]} but could not figure out which cloud provider this belongs to.'
        )

    # Sanity checking of various arguments
    supported_priority_types = ["ON_DEMAND_ECONOMY", "ON_DEMAND_PRIORITY"]
    if priority not in supported_priority_types:
        raise HtcException(
            f"During job creation, priority was set to unsupported value {priority}. Valid values are {supported_priority_types}"
        )

    if not isinstance(envs, list):
        raise HtcException(
            f"During job creation, the envs argument is not a list: {envs}"
        )

    if not isinstance(commands, list):
        raise HtcException(
            "During job creation, the commands argument is not a list. Expected e.g. "
            "['bash', '-c', 'echo hello world'], "
            f"got {commands}"
        )

    for env in envs:
        if not isinstance(env, dict) or set(env.keys()) != set(["name, value"]):
            raise HtcException(
                f"During job creation, the envs argument is not formatted as a list of dicts. "
                'Expected list of dicts: [{"name": "MY_ENV_VAR", "value": "value_of_my_env_var"},..],  '
                f"got {envs}"
            )

    for claim in claims:
        if not isinstance(claim, dict) or set(claim.keys()) != set(["name", "value"]):
            raise HtcException(
                f"During job creation, the claims argument is not formatted as a list of dicts. "
                'Expected list of dicts: [{"name": "my_claim_name", "value": "my_claim_value"},..],  '
                f"got {claims}"
            )

    supported_architecture_types = ["AARCH64", "A100", "X86"]
    if architecture not in supported_architecture_types:
        raise HtcException(
            f"During job creation, architecture was set to unsupported value {architecture}. Valid values are {supported_architecture_types}"
        )

    payload = [
        {
            "jobName": job_name,
            "batchSize": batch_size,
            "tags": batch_tags,
            "region": selected_region,
            "cloudProvider": cloud_provider,
            "htcJobDefinition": {
                "imageName": image_name,
                "maxVCpus": max_vcpus,
                "maxMemory": max_memory_mib,
                "maxDiskGiB": max_disk_gib,
                "maxSwap": max_swap_mib,
                "tags": job_tags,
                "commands": commands,
                "envs": envs,
                "claims": claims,
                "execTimeoutSeconds": exec_timeout_seconds,
                "architecture": architecture,
                "priority": priority,
            },
        }
    ]
    return create_job_batch_raw(rescale, task, payload=payload)


def create_job_batch_raw(
    rescale: HtcSession, task: HtcTask, payload: list[dict]
) -> HtcJobBatch:
    """
    This function creates batch of Rescale jobs.

    :param payload: The full JSON dict expected by the POST /htc/projects/{projectId}/tasks/{taskId}/jobs/batch endpoint

    Most users should use :func:`create_job_batch` instead of this raw function. That function
    accepts separate arguments for the individual fields instead of the full JSON dict.
    """
    if isinstance(task, HtcTask):
        task_id = task.json["taskId"]
        project_id = task.json["projectId"]
    else:
        raise HtcException("Provided argument task is not a HtcTask object.")

    # Wait for the image to transition to the ready stage
    # Loop over each batch definition if there are multiple
    for job_batch in payload:
        waited_for = 0
        wait_interval = 10
        image_name = job_batch["htcJobDefinition"]["imageName"]
        while True:
            if waited_for > MAX_WAIT_FOR_IMAGE_TRANSITION_PENDING_READY_SECONDS:
                raise HtcException(
                    f"While waiting for {image_name} to transition from PENDING to READY, waited longer than timeout {MAX_WAIT_FOR_IMAGE_TRANSITION_PENDING_READY_SECONDS}."
                )
            image_status = api.get_htc_projects_container_registry_images(
                rescale, task.project.json["projectId"], image_name
            )

            # When the image is ready, continue
            if image_status["status"] == "READY":
                break
            elif image_status["status"] == "PENDING":
                waited_for += wait_interval
                time.sleep(wait_interval)
            else:
                raise HtcException(
                    f"Unexpected status of an image recieved, got {image_status} for {image_name}."
                )

    res = api.post_htc_projects_tasks_jobs_batch(
        rescale, project_id, task_id, payload=payload
    )
    # We only support a single batch per API call here, so safe to
    # index into the first one.
    return HtcJobBatch(res[0], task)


# A generator that returns the lines of a file in reverse order
def reverse_readline(fh, buf_size=8192):
    segment = None
    offset = 0
    fh.seek(0, os.SEEK_END)
    file_size = remaining_size = fh.tell()
    while remaining_size > 0:
        offset = min(file_size, offset + buf_size)
        fh.seek(file_size - offset)
        buffer = fh.read(min(remaining_size, buf_size)).decode(encoding="utf-8")
        remaining_size -= buf_size
        lines = buffer.split("\n")
        # The first line of the buffer is probably not a complete line so
        # we'll save it and append it to the last line of the next buffer
        # we read
        if segment is not None:
            # If the previous chunk starts right from the beginning of line
            # do not concat the segment to the last line of new chunk.
            # Instead, yield the segment first
            if buffer[-1] != "\n":
                lines[-1] += segment
            else:
                yield segment
        segment = lines[0]
        for index in range(len(lines) - 1, 0, -1):
            if lines[index]:
                yield lines[index]
    # Don't yield None if the file was empty
    if segment is not None:
        yield segment
