"""
This module has functions that help with Rescale Tasks.
Tasks are returned as a RescaleTask object, which can
be used for later library calls.
"""
from __future__ import annotations
from datetime import timedelta, datetime
from .internals.constants import FLOOD_PREVENTION_INTERVAL_SECONDS
from .exceptions import RescaleException
from .rprojects import RescaleProject
from . import RescaleSession, api
from .logger import logger


class RescaleTask:
    """
    Class which represents a single Rescale Task. Use the functions in
    rescalectrl.tasks to create this object.
    """

    def __init__(self, json: dict, project: RescaleProject):
        if not isinstance(project, RescaleProject):
            raise RescaleException(
                "Provided project argument is not a RescaleProject object."
            )
        self.json = json
        """The raw dictionary describing this Task. The dictionary follows the
        HTCTask schema in the Rescale HTC API documentation. Example contents:

        .. code-block:: json

            {
                "projectId": "project-12345",
                "taskId": "task-12345",
                "taskName": "my-task",
                "taskDescription": "my sample task",
                "createdBy": "qWoUF",
                "createdAt": "2023-10-19T10:00:55.370Z",
                "workspaceId": "04-8473942",
                "taskFolderPath": "projects/project-12345/tasks/task-12345",
                "lifecycleStatus": "ACTIVE"
            }

        Access this member variable to extract information about a task.
        """

        self.project = project
        now = datetime.now()
        self.task_summary_updated_at = now - timedelta(hours=1)
        self.task_summary = None

    def __repr__(self):
        return "RescaleTask(" + str(self.json) + ")"

    def get_task_summary(self, rescale: RescaleSession) -> dict:
        """
        Returns the task summary for this RescaleJobBatch's task.
        This contains summary of how many jobs are running, succeeded,
        failed etc within this task. Example return value:

        .. code-block:: json

            {
                "group": null,
                "jobStatuses": {
                    "SUBMITTED_TO_RESCALE": 1,
                    "SUBMITTED_TO_PROVIDER": 0,
                    "RUNNABLE": 0,
                    "STARTING": 0,
                    "RUNNING": 0,
                    "SUCCEEDED": 0,
                    "FAILED": 0
                },
                "still_running": true
            }

        Adds a field called "still_running" to the return dict, which
        is true if any container is in any state not equal to SUCCEEDED
        or FAILED.

        This function has basic flood prevention on the job status requests.
        The API never updates more than every 30 seconds anyway, so calling
        this function more often than that has no effect.
        """
        now = datetime.now()

        time_since_last_update = now - self.task_summary_updated_at
        if time_since_last_update > timedelta(
            seconds=FLOOD_PREVENTION_INTERVAL_SECONDS
        ):
            self.task_summary = api.get_htc_projects_tasks_summary_statistics(
                rescale, self.json["projectId"], self.json["taskId"]
            )
            logger.debug(f"Updated task summary, task id {self.json['taskId']}")
            self.task_summary["still_running"] = (
                self.task_summary["jobStatuses"]["SUBMITTED_TO_RESCALE"] > 0
                or self.task_summary["jobStatuses"]["SUBMITTED_TO_PROVIDER"] > 0
                or self.task_summary["jobStatuses"]["RUNNABLE"] > 0
                or self.task_summary["jobStatuses"]["STARTING"] > 0
                or self.task_summary["jobStatuses"]["RUNNING"] > 0
            )
            self.task_summary_updated_at = datetime.now()
        else:
            logger.debug(
                f"Skipped updating task summarys since last request was {time_since_last_update} ago, less than {FLOOD_PREVENTION_INTERVAL_SECONDS} seconds, taskId {self.json['taskId']}"
            )

        return self.task_summary

    def is_still_running(self, rescale: RescaleSession) -> bool:
        """
        Returns false if all jobs within this task are in the SUCCEEDED or FAILED states,
        otherwise return true as one or more jobs are still running/pending.
        Equivalent to the "still_running" field in
        :func:`rescalectrl.rtasks.RescaleTask.get_task_summary`.

        Use this function in a loop with 30 second intervals to wait for job completion.

        .. code-block:: python

            while task.is_still_running():
                time.sleep(30)
            print("Completed all jobs in task")
            print(task.get_task_summary())

        This function has basic flood prevention on the job status requests.
        The API never updates more than every 30 seconds anyway, so calling
        this function more often than that has no effect.
        """
        return self.get_task_summary(rescale)["still_running"]

    def delete_task(self, rescale: RescaleSession):
        """
        Delete this task.
        """
        delete_task_with_id(rescale, self.project, self.json["taskId"])

    def cancel_jobs_in_task(self, rescale: RescaleSession):
        """
        Cancels all the jobs within this task. Tasks that have not yet started
        will not start, and running tasks will be stopped.
        """
        api.post_htc_projects_tasks_jobs_cancel(
            rescale, self.project.json["projectId"], self.json["taskId"]
        )


def get_tasks_with_name(
    rescale: RescaleSession,
    project: RescaleProject,
    task_name: str,
    lifecycle_status: str = "ACTIVE",
) -> list[RescaleTask]:
    """
    Get a list of tasks that match a certain name, within a given project and matching
    a given lifecycle_status. To find tasks in any lifecycle_status task, set lifecycle_status to
    ``any``. Returns a list of RescaleTask objects.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )

    any_lifecycle_status = True if lifecycle_status in ["any", "all", None] else False

    all_tasks = api.get_htc_projects_tasks(rescale, project_id)
    name_matching_tasks = [
        RescaleTask(task_json, project)
        for task_json in all_tasks
        if task_json["taskName"] == task_name
        and (any_lifecycle_status or task_json["lifecycleStatus"] == lifecycle_status)
    ]
    return name_matching_tasks


def get_task_with_id(
    rescale: RescaleSession, project: RescaleProject, task_id: str
) -> RescaleTask:
    """
    Get a task with a certain taskId, within a given project.

    If the taskId is not found, returns None.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )

    try:
        task = api.get_htc_projects_tasks(rescale, project_id, task_id)
    except RescaleException as e:
        # A 404 exception means a task with this id was not found
        return None

    return RescaleTask(task, project)


def get_tasks(
    rescale: RescaleSession, project: RescaleProject, lifecycle_status: str = "ACTIVE"
) -> list[RescaleTask]:
    """
    Get all tasks within a given project that matches a given lifecycle_status.
    To find tasks in any lifecycle_status task, set lifecycle_status to
    ``any``. Returns a list of RescaleTask objects.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )

    any_lifecycle_status = True if lifecycle_status in ["any", "all", None] else False

    all_tasks = api.get_htc_projects_tasks(rescale, project_id)
    name_matching_tasks = [
        RescaleTask(task_json, project)
        for task_json in all_tasks
        if (any_lifecycle_status or task_json["lifecycleStatus"] == lifecycle_status)
    ]
    return name_matching_tasks


def create_task_with_name(
    rescale: RescaleSession, project: RescaleProject, task_name, task_description=""
) -> RescaleTask:
    """
    Create a Rescale task with a specific task name, and an optional task description.

    Returns a RescaleTask object.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )

    task_definition = {"taskName": task_name, "taskDescription": task_description}
    return RescaleTask(
        api.post_htc_projects_tasks(rescale, project_id, payload=task_definition),
        project,
    )


def delete_tasks_with_name(
    rescale: RescaleSession, project: RescaleProject, task_name: str
) -> list[dict]:
    """
    Delete all tasks that match a specific task name. This may delete multiple
    tasks. Returns a list of json descriptions of the tasks that were deleted, or
    an empty list if no tasks where affected.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )
    all_tasks = get_tasks(rescale, project, lifecycle_status="ACTIVE")
    logger.debug(
        f"delete_tasks_with_name: Found {len(all_tasks)} tasks with lifecyleStatus ACTIVE"
    )
    name_matching_tasks = [
        task for task in all_tasks if task.json["taskName"] == task_name
    ]
    logger.debug(
        f"delete_tasks_with_name: Of these, taskIDs {[task.json['taskId'] for task in name_matching_tasks]} "
        f"match the name {task_name} and will be deleted"
    )

    tasks_deleted = []
    for task_to_delete in name_matching_tasks:
        tasks_deleted.append(
            api.delete_htc_projects_tasks(
                rescale, project_id, task_to_delete.json["taskId"]
            )
        )
    return tasks_deleted


def delete_task_with_id(
    rescale: RescaleSession, project: RescaleProject, task_id: str
) -> dict:
    """
    Delete a task matching a given ID within the provided project. The json describing
    the deleted task is returned.

    None is returned if the taskId does not exist.
    """
    if isinstance(project, RescaleProject):
        project_id = project.json["projectId"]
    else:
        raise RescaleException(
            "Provided project argument is not a RescaleProject object."
        )

    try:
        return api.delete_htc_projects_tasks(rescale, project_id, task_id)
    except RescaleException as e:
        if e.status_code == 404:
            # A 404 exception means a task with this id was not found
            return None
        else:
            raise
