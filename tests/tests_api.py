import copy
from typing import Iterator
import unittest
from unittest import mock
import time
import threading
import os
import logging
import shutil
import api_flask_mock

# Unittest specific overrides, to be mocked into the rescalehtc module
TEST_CONFIG_FOLDER = os.path.dirname(os.path.abspath(__file__)) + "/tmp_configfolder/"
TEST_BASE_URL = "http://127.0.0.1:5000"

# Enable verbose logging during test
import logging
logging.basicConfig(level=logging.NOTSET)

# Library under test
import rescalehtc
from rescalehtc import api
from rescalehtc.api import *

class TestsHighlevel(unittest.TestCase):

    # Start flask, to be run in a thread
    def start_flask():
        api_flask_mock.app.run()

    # Prepare tests by starting Flask as a mock API
    def setUpClass():
        flask_thread = threading.Thread(target=TestsHighlevel.start_flask, daemon=True)
        flask_thread.start()
        time.sleep(0.5)

        # Create a config folder with a mock API key
        shutil.rmtree(TEST_CONFIG_FOLDER, ignore_errors=True)
        os.makedirs(TEST_CONFIG_FOLDER + "/default")
        with open(TEST_CONFIG_FOLDER + "/default/rescale_api_token.txt", "w") as fp:
            fp.write("mock-api-key==")

    def setUp(self):
        if "RESCALEHTC_MOCK_TARGET_STATUS" in os.environ:
            del os.environ["RESCALEHTC_MOCK_TARGET_STATUS"]
        # Mock URL and config folder in authenticate module
        with mock.patch.multiple("rescalehtc.htcsession.HtcSession",
                get_rescale_api_base_url=lambda : TEST_BASE_URL,
                get_config_folder=lambda _ : TEST_CONFIG_FOLDER,
            ):
            self.rs = rescalehtc.htcsession.HtcSession()
        # Empty line to separate tests
        print()


    ############ Actual tests ###################

    def test_token_calls(self):
        get_well_known_jwks(self.rs)
        get_auth_token(self.rs, "auth header example")
        get_auth_token_whoami(self.rs)
        get_auth_whoami(self.rs, "auth header example")

        try:
            post_oauth_token(self.rs)
            raise Exception
        except NotImplementedError:
            pass # Expecting this to give exception

    def test_api_provider_resource(self):
        get_htc_gcp_clusters(self.rs, "workspace_example_id")
        get_htc_regions(self.rs)
        get_htc_regions(self.rs, "example_region")

    def test_api_metrics_resource(self):
        try:
            get_htc_metrics(self.rs)
            raise Exception
        except HtcException:
            pass # Expecting this to give exception

    def test_api_project_resource(self):
        get_htc_projects(self.rs, "example_project_id")
        post_htc_projects(self.rs, {"random": "payload"})

        get_htc_projects_dimensions(self.rs, "example_project_id")
        put_htc_projects_dimensions(self.rs, "example_project_id", {"random": "payload"})
        get_htc_projects_limits(self.rs, "example_project_id")
        get_htc_projects_limits(self.rs, "example_project_id", "limit_id")
        post_htc_projects_limits(self.rs, "example_project_id", {"random": "payload"})

        delete_htc_projects_limits(self.rs, "example_project_id")
        delete_htc_projects_limits(self.rs, "example_project_id", 42)
        patch_htc_projects_limits(self.rs, "example_project_id", "resource_limit_id", {"random": "payload"})
        get_htc_projects_storage_presigned_url(self.rs, "example_project_id")
        get_htc_projects_storage_token(self.rs, "example_project_id")
        get_htc_projects_storage_token(self.rs, "example_project_id", "example_region")
        get_htc_projects_storage_tokens(self.rs, "example_project_id")

        get_htc_projects_task_retention_policy(self.rs, "example_project_id")
        put_htc_projects_task_retention_policy(self.rs, "example_project_id", {"random": "payload"})
        delete_htc_projects_task_retention_policy(self.rs, "example_project_id")

    def test_api_container_registry_resource(self):
        get_htc_projects_container_registry_images(self.rs, "example_project_id", "image_name")
        post_htc_projects_container_registry_repo(self.rs, "example_project_id", "repo_name")
        get_htc_projects_container_registry_token(self.rs, "example_project_id")

    def test_api_task_resource(self):
        get_htc_projects_tasks(self.rs, "example_project_id")
        get_htc_projects_tasks(self.rs, "example_project_id", "task_id")
        post_htc_projects_tasks(self.rs, "example_project_id", "task_id")
        delete_htc_projects_tasks(self.rs, "example_project_id", "task_id")
        patch_htc_projects_tasks(self.rs,  "example_project_id", "task_id", {"random":"payload"})
        get_htc_projects_tasks_group_summary_statistics(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_groups(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_storage_presigned_url(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_storage_regional_storage(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_storage_token(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_storage_token(self.rs, "example_project_id", "task_id", "region")
        get_htc_projects_tasks_storage_tokens(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_summary_statistics(self.rs, "example_project_id", "task_id")

    def test_api_job_resource(self):
        get_htc_projects_tasks_jobs(self.rs, "example_project_id", "task_id")
        post_htc_projects_tasks_jobs_batch(self.rs, "example_project_id", "task_id", {"random":"payload"})
        post_htc_projects_tasks_jobs_cancel(self.rs, "example_project_id", "task_id")
        get_htc_projects_tasks_jobs_logs(self.rs, "example_project_id", "task_id", "job_id")
        get_htc_projects_tasks_jobs_events(self.rs, "example_project_id", "task_id", "job_id")

    def test_api_storage_resource(self):
        get_htc_storage(self.rs)
        get_htc_storage_region(self.rs, "region")

    def test_api_workspace_resource(self):
        get_htc_workspaces_dimensions(self.rs, "workspace_example_id")
        get_htc_workspaces_limits(self.rs, "workspace_example_id")
        get_htc_task_retention_policy(self.rs, "workspace_example_id")
        put_htc_task_retention_policy(self.rs, "workspace_example_id", {"random": "payload"})

