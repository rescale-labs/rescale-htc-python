"""
This module holds functions that deal with Rescale Projects.
Projects are returned as a HtcProject object, which can
be used for later library calls.
"""
from __future__ import annotations
from .exceptions import HtcException
from . import HtcSession, api


class HtcProject:
    """
    Class which represents a single Rescale Project. Use the functions in
    rescalehtc.projects to create this object.
    """

    def __init__(self, json : dict):
        self.json : dict = json
        """The raw dictionary describing this Project. The dictionary follows the
        HTCProject schema in the Rescale HTC API documentation. Example contents:

        .. code-block:: json

            {
                "projectId": "project-12345",
                "projectName": "my-project",
                "projectDescription": "my-first-project",
                "createdBy": "qWoUF",
                "workspaceId": "04-8473942",
                "organizationCode": "my-org",
                "createdAt": "2023-10-19T10:01:40.471Z",
                "containerRegistry": "123456789.dkr.ecr.us-west-2.amazonaws.com/rescale/project-12345/",
                "repositories": [
                    "repo1",
                    "repo2"
                ],
                "regions": [
                    "AWS_US_EAST_2",
                    "AWS_US_WEST_2"
                ],
                "regionSettings": [
                    {
                    "computeSettings": {
                        "computeRegion": "AWS_AP_SOUTHEAST_1"
                    },
                    "storageSettings": {
                        "storageRegion": "AWS_AP_SOUTHEAST_1"
                    }
                    }
                ],
                "projectFolderPath": "projects/project-12345/"
            }

        Access this member variable to extract information about a project.
        """

    def __repr__(self):
        return "HtcProject(" + str(self.json) + ")"

    def get_limits(self, rescale: HtcSession) -> list[dict]:
        """
        Return the limits that are applied to this project, for example
        the maximum concurrect vCPU count that can be used. Returns a
        list of limits, as multiple kinds of limits may be applied at once.
        """
        return api.get_htc_projects_limits(rescale, self.json["projectId"])

    def set_vcpu_limit(self, rescale: HtcSession, modifier_role: str, vcpu_limit: int):
        """
        Set the maximum concurrent number of vCPUs for this project. This
        may require certain privileges.
        """
        valid_modifier_roles = ["PROJECT_ADMIN", "WORKSPACE_ADMIN"]
        if modifier_role not in valid_modifier_roles:
            raise HtcException(
                f"Provided modifier_role {modifier_role} is not a valid one ({valid_modifier_roles})"
            )
        if not vcpu_limit > 0:
            raise HtcException(f"vCPU limit is not a valid value: {vcpu_limit}")
        return api.post_htc_projects_limits(
            rescale,
            self.json["projectId"],
            {"modifierRole": modifier_role, "vCPUs": vcpu_limit},
        )


def get_projects(rescale: HtcSession) -> list[HtcProject]:
    """
    Get all the projects available in the current workspace.
    Return the projects as HtcProject objects.
    """
    projects = api.get_htc_projects(rescale)
    if len(projects) == 0:
        return None
    return [HtcProject(project) for project in projects]


def get_project_with_name(rescale: HtcSession, project_name: str) -> HtcProject:
    """
    Get a single project within this workspace that matches the given name.
    Return the project as a HtcProject. Returns None if no matching
    project was found. Throws an exception if the workspace contains several
    projects with the same name.
    """
    projects = api.get_htc_projects(rescale)
    matching_projects = [
        project for project in projects if project["projectName"] == project_name
    ]
    if len(matching_projects) == 1:
        return HtcProject(matching_projects[0])
    elif len(matching_projects) == 0:
        return None
    else:
        raise HtcException(
            f"More than one project with the name {project_name} found in projects list {projects}"
        )


def get_project_with_id(rescale: HtcSession, project_id: str) -> HtcProject:
    """
    Get a single project within this workspace with a specific ID.
    Return the project as a HtcProject. Returns None if no matching
    project was found.
    """
    try:
        project = api.get_htc_projects(rescale, project_id=project_id)
    except HtcException as e:
        # If we didn't find a project with this ID (indicated by 404) then return None
        if e.status_code == 404:
            return None
        # Any other HTTP error is raised as an exception.
        else:
            raise

    return HtcProject(project)
