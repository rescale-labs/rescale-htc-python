Examples
========

This page holds various examples for how you could use the ``rescalehtc``
library.


Running a single job on Rescale
--------------------------------

Below shows a complete and runnable example that shows how you could run a
container on Rescale. The example pulls the docker hello-world container,
authenticates and pushes it to the container registry, submits a Rescale job to
run it, waits for it to complete, downloads the logs and finally cleans up the
task at the end.

This example is standalone and can be run as-is.

.. code-block:: python

    import time
    from subprocess import run
    from rescalehtc import HtcSession, htcprojects, htctasks, htcjobs, container_registry

    # Authenticate
    htcs = HtcSession()

    # Find all the rescale projects, and just pick the first one
    # In production use you should use get_project_with_name() here.
    all_projects = htcprojects.get_projects(htcs)  # projects.HtcProject
    project = all_projects[0]

    # Access the rescale container registry
    registry = container_registry.get_container_registry(htcs, project)

    # We want to run this container in the cloud, pull it from docker hub:
    local_image_name = "hello-world:latest"
    run(f"docker pull {local_image_name}", shell=True, check=True)

    # Push the image to the rescale container registry
    registry_image_name = registry.push_docker_image(htcs, local_image_name)

    # Create a task for the run
    task = htctasks.create_task_with_name(htcs, project, task_name="my_hello_world_task")

    # Run the job!
    job = htcjobs.create_single_job(
        htcs,
        task,
        priority="ON_DEMAND_PRIORITY",
        image_name=registry_image_name,
        exec_timeout_seconds=3 * 60,
    )

    # Wait for the jobs in the task to complete
    while job.is_still_running(htcs):
        print(f"Job still running, current status: {job.json['status']}")
        time.sleep(15)
    print("Job done.")

    # Show the log output
    print("Log:")
    log = job.get_logs(htcs)
    print("\n".join(log))

    # Housekeeping: Delete the task we used
    htctasks.delete_tasks_with_name(htcs, project, "my_hello_world_task")


Running batch runs of containers
--------------------------------

To run larger number of containers in parallel, use the batch features.

This example shows how to start 20 parallel containers, waiting for their
completion, then fetching the logs for each of them.

In general you should avoid having to fetch logs from containers, instead to try
build batch processing solutions where your results are pushed to some external
data store (for example Rescale Object Storage with the ``htcctl`` utility) or a
database.

Within your container, use the ``AWS_BATCH_JOB_ARRAY_INDEX`` env variable as the
indicator for which number in the batch a container has.

See the Rescale HTC documentation for more details on how to build good batch
flows.

This example assumes the same initial setup as in previous examples, including
getting the project and registry and so on.

.. code-block:: python

    # We want to use alpine:latest as our container
    local_image_name = "alpine:latest"
    run(f"docker pull {local_image_name}", shell=True, check=True)

    # Push the image to the rescale container registry
    registry_image_name = registry.push_docker_image(htcs, local_image_name)

    # Create a task for the run
    task = htctasks.create_task_with_name(htcs, project, task_name="my_batch_example_task")

    # Run the batch set of jobs
    job_batch = htcjobs.create_job_batch(
        htcs,
        task,
        batch_size=20,
        priority="ON_DEMAND_PRIORITY",
        image_name=registry_image_name,
        commands=["sh", "-c", "echo Hello from the container, my index was ${AWS_BATCH_JOB_ARRAY_INDEX}"],
        exec_timeout_seconds=3 * 60,
    )

    # Wait for the jobs in the task to complete
    while job_batch.is_still_running(htcs):
        print(f"Job batch still running, current status: {job_batch.get_task_summary(htcs)}")
        time.sleep(15)
    print("Job batch done.")

    jobs = job_batch.to_jobs()

    # Show the log output for each container.
    # For production usage you should not pull down logs from each container,
    # instead upload the logs or artifacts to object storage or a database,
    # as pulling logs through the API isn't scalable to large number of jobs.
    print("Fetching logs from each container:")
    for job in jobs:
        print("\n".join(job.get_logs(htcs)))

    # Housekeeping: Delete the task we used
    htctasks.delete_tasks_with_name(htcs, project, "my_batch_example_task")


Using the the low level API
---------------------------

In some cases you don't want to use the high level functions of this library,
and then instead access the Rescale API more directly.

This library exposes (nearly) every single API endpoint as a convenient
function. This lets you use the API directly while still getting the benefits of
automatic authentication, token renewal and pagination support.

.. code-block:: python

    from rescalehtc import HtcSession, api

    # Authenticate
    rs = HtcSession()

    # See the available regions in your workspace
    all_regions = api.get_htc_regions(rs)
    print(all_regions)

    # Get information on a single region
    region = all_regions[0]
    region_name = region["region"]
    region_info = api.get_htc_regions(rs, region=region_name)
    print(region_name, region_info)