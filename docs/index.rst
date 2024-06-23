rescalehtc Documentation: Rescale Control Helpers
=================================================

This library contains convenient methods for dealing with Rescale HTC in Python,
for running batch containers in the cloud.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   Overview and Getting Started <self>
   examples
   htcsession
   projects
   tasks
   jobs
   container_registry
   bearer_token
   plumbing
   exceptions
   versioning
   Developer information <developers>

The library is available as a pip module.


Overview
========

This library provides 3 main features:

* A convenient class-based wrapper around Rescale HTC Projects, Tasks, Jobs and
  more, with helper functions to do common operations.
* Low-level plumbing functions that correspond 1:1 with the Rescale HTC REST
  API.
* Automatic and transparent authentication and bearer token renewal, including
  support for multiple workspaces.

You can use only the parts of the library you need.

The library takes care of authentication including automatic and transparent
renewal of bearer tokens, so you don't have to worry about expired tokens. It
works both inside running Rescale containers or locally, using either refresh
tokens or API tokens. You set it up once using the command line utilities
locally, or if you're running within a container in Rescale it picks up
credentials from the environment automatically.


Getting started
===============

After installing the library, start by providing your authentication credentials
using the included executable ``rauthenticate``.

This step will write tokens to ~/.config/rescalehtc/[...] for later use.

If you are in an interactive environment, do:

``> rauthenticate --interactive``

This will prompt you for your API key, which you obtain from
https://platform.rescale.com/user/settings/api-key/

If you're using this package in a non-interactive environment (e.g. in a
container or CI job), then do

``> rauthenticate``

This will instead look for environment variables with either a
RESCALE_HTC_REFRESH_TOKEN or RESCALE_API_TOKEN, which will be used to obtain the
Bearer token used for later operations. This is similar to Rescale's htcctl
utility behavior.

With authentication complete, you are now ready to use the library.


Getting started with using the library
======================================

After setting up the environment using ``rauthenticate``, you
can now use the API in your python code.

Below shows a complete and runnable example that shows how you
could run a container on Rescale. The example pulls the docker hello-world
container, authenticates and pushes it to the container registry, submits
a Rescale job to run it, waits for it to complete, downloads the logs and
finally cleans up the task at the end.

::

   import time
   from subprocess import run
   import rescalehtc
   from rescalehtc import htcprojects, htctasks, htcjobs, container_registry

   # Authenticate
   htcs = rescalehtc.HtcSession()

   # Find a Rescale project by name
   project = htcprojects.get_project_with_name(htcs, "pj_my_rescale_project_name")

   # Get a container registry token
   registry = container_registry.get_container_registry(htcs, project)

   # We want to run this container in the cloud:
   local_image_name = "hello-world:latest"
   run(f"docker pull {local_image_name}", shell=True, check=True)

   # Push the image to the cloud registry
   registry_image_name = registry.push_docker_image(htcs, local_image_name)

   # Create a task for the run
   task = htctasks.create_task_with_name(htcs, project, task_name="my_hello_world_task")

   # Run the job!
   job_batch = htcjobs.create_job_batch(
      htcs,
      task,
      batch_size=1,
      priority="ON_DEMAND_PRIORITY",
      image_name=registry_image_name,
      exec_timeout_seconds=3 * 60,
   )
   # Wait for the jobs in the task to complete
   while (task_summary := job_batch.get_task_summary(htcs))["still_running"]:
      print(f"Job still running: {task_summary}")
      time.sleep(15)
   print("Job done.")

   # Show the log output
   print("Log:")
   log = job_batch.to_jobs()[0].get_logs(htcs)
   print("\n".join(log))

   # Housekeeping: Delete the task we used
   htctasks.delete_tasks_with_name(htcs, project, "my_hello_world_task")


And much more. See the documentation for the various modules for more details.

As a general rule, this library calls the Rescale HTC API **only** when you use
functions where you need to pass in the HtcSession object ("htcs" in example
above).


HtcSession
========== 

.. automodule:: rescalehtc.htcsession
   :members:
   :no-index:


HTC Projects
============

.. automodule:: rescalehtc.htcprojects
   :no-index:

   To see how to construct or use HtcProject objects, go to :doc:`projects`.


HTC Tasks
=========

.. automodule:: rescalehtc.htctasks
   :no-index:

   To see how to construct or use HtcTask objects, go to :doc:`tasks`.


HTC Jobs and JobBatch
=====================

.. automodule:: rescalehtc.htcjobs
   :no-index:

   To see how to construct or use HtcJob/HtcJobBatch objects, go to :doc:`jobs`.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
