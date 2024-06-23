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
from rescalehtc import api, htcjobs, htcprojects, htctasks, container_registry

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

    # Test listing projects
    def test_0001_list_projects(self):

        projects = rescalehtc.htcprojects.get_projects(self.rs)
        assert(len(projects) > 0)

    # Test listing tasks
    def test_0002_list_tasks(self):
        projects = rescalehtc.htcprojects.get_projects(self.rs)
        assert(len(projects) > 0)
        project = projects[0]
        tasks = rescalehtc.htctasks.get_tasks(self.rs, project)
        assert(len(tasks) > 0)

    # Test listing jobs, and check types of all the returns
    def test_0003_list_jobs(self):
        projects = rescalehtc.htcprojects.get_projects(self.rs)
        assert(len(projects) > 0)
        assert(all(isinstance(project, rescalehtc.htcprojects.HtcProject) for project in projects))
        project = projects[0]
        tasks = rescalehtc.htctasks.get_tasks(self.rs, project)
        assert(len(tasks) > 0)
        assert(all(isinstance(task, rescalehtc.htctasks.HtcTask) for task in tasks))
        task = tasks[0]
        jobs = rescalehtc.htcjobs.get_jobs(self.rs, task)
        assert(len(jobs) > 0)
        assert(all(isinstance(job, rescalehtc.htcjobs.HtcJob) for job in jobs))

    def test_0010_basic_exception_handling(self):
        os.environ["RESCALEHTC_MOCK_TARGET_STATUS"] = "403"
        # If the API returns a 403 status, then expect a HtcException with that exit code
        try:
            projects = rescalehtc.htcprojects.get_projects(self.rs)
            assert(False)
        except rescalehtc.exceptions.HtcException as e:
            assert(e.status_code == 403)

    # Perform assorted operations on the container registry object
    def test_0050_container_registry_operations(self):
        project = rescalehtc.htcprojects.get_projects(self.rs)[0]
        registry = container_registry.get_container_registry(self.rs, project)
        # TODO: Reenable this if the delete image endpoint is added back into the API
        #delete_result = registry.delete_image(self.rs, image_name="image-to-delete:latest")
        create_result = registry.create_repo(self.rs, container_repo_name="image-to-check")
        img_status_result = registry.is_image_ready(self.rs, image_name="image-to-check:latest")
        img_details = registry.get_image(self.rs, image_name="image-to-check:latest")
        repos = registry.get_repos(self.rs)
        images = registry.get_images(self.rs)
        token = registry.get_token(self.rs)

    def test_0070_project_operations(self):
        project = rescalehtc.htcprojects.get_projects(self.rs)[0]
        limits = project.get_limits(self.rs)

    def test_0070_task_operations(self):
        project = rescalehtc.htcprojects.get_projects(self.rs)[0]
        task = htctasks.get_tasks(self.rs, project)[0]
        task.get_task_summary(self.rs)
        assert(isinstance(task.is_still_running(self.rs), bool))
        task.cancel_jobs_in_task(self.rs)
        task.delete_task(self.rs)

    def test_0080_job_operations(self):
        project = rescalehtc.htcprojects.get_projects(self.rs)[0]
        task = htctasks.get_tasks(self.rs, project)[0]
        job = htcjobs.get_job_with_id(self.rs, task, "1234567-89")

        # Try job updates etc
        assert(isinstance(job.is_still_running(self.rs), bool))
        assert(isinstance(job.get_update(self.rs), dict))

        # Fetch the log twice, to ensure that log caching works
        for _ in range(2):
            # Fetch logs from this job
            log_iter = job.get_logs(self.rs)
            # Should be an iterator
            assert(isinstance(log_iter, Iterator))
            log_str = "\n".join(log_iter)
            # Log message should be the one from the API docs
            assert(log_str == "JOB COMPLETED SUCCESSFULLY")

        # Trivial test to check if setting a line limit works
        log_iter = job.get_logs(self.rs, last_n_lines=1)
        assert(len(list(log_iter)) == 1)

        # Fetch logs to a file
        tmp_logfile = "tmp_logfile.txt"
        if os.path.isfile(tmp_logfile):
            os.remove(tmp_logfile)
        job.get_logs_to_file(self.rs, tmp_logfile, last_n_lines=30)
        # Should have written a file now
        assert(os.path.isfile(tmp_logfile))
        job.get_logs_to_file(self.rs, tmp_logfile)
        # Should have written a file now
        assert(os.path.isfile(tmp_logfile))
        with open(tmp_logfile) as fp:
            file_log = fp.read()
        # Check that the logfile matches the normal string-return log read
        assert(log_str+"\n" == file_log)
        # Cleanup
        os.remove(tmp_logfile)

    def test_0090_job_creation(self):
        project = rescalehtc.htcprojects.get_projects(self.rs)[0]
        task = htctasks.get_tasks(self.rs, project)[0]

        job = htcjobs.create_single_job(self.rs, task, "ON_DEMAND_ECONOMY", "my_image:latest", exec_timeout_seconds=10, region="AWS_US_EAST_2")


    def test_0200_jwt_tests(self):
        # The JWT provided by the HTC docs API example isn't a JWT, so
        # we need to temporarily fake one
        original_rs = copy.deepcopy(self.rs)

        testcase_bearer = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJ1c2VyRGVmaW5lZF9teWNsYWltIjoiaGVsbG93b3JsZCJ9.P2KrRG__0hvPYUAdXvFKpXVZc_l77sLZM8B9p41RYak"
        self.rs.bearer_json["tokenValue"] = testcase_bearer
        self.rs.RESCALE_HTC_BEARER_TOKEN = testcase_bearer

        # The testing part, getting the token and the claims
        jwt = self.rs.get_bearer_token()
        user_claims = jwt.get_user_claims()
        assert(user_claims == {"myclaim": "helloworld"})

        # Restore the rs object
        self.rs.bearer_json["tokenValue"] = original_rs
        self.rs.RESCALE_HTC_BEARER_TOKEN = original_rs

    # Test the various endpoints in Token Resource
    def test_0500_token_resource_tests(self):
        # Get a bearer token
        bearer = api.get_auth_token(self.rs, authorization_header="Token ABCD")
        # Get the payload from a bearer token
        whoami = api.get_auth_token_whoami(self.rs)
        # Get some standalone whoami info
        whoami_token = api.get_auth_whoami(self.rs, authorization_header="Token ABCD")
        # Fetch the JWK
        jwk = api.get_well_known_jwks(self.rs)
