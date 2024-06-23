import os

# These two should never be imported directly, as they're mocked
# during tests. Use the member variables of HtcSession object instead.
_RESCALE_API_BASE_URL = "https://htc.rescale.com/api/v1"
_CONFIG_FOLDER = os.path.expanduser("~/.config/rescalehtc")

# List of all the valid job statuses
VALID_JOB_STATUSES = [
    "SUBMITTED_TO_RESCALE",
    "SUBMITTED_TO_PROVIDER",
    "RUNNABLE",
    "STARTING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
]

# Guard certain function calls with floor prevention, for example
# the status update functions on jobs. Restrict how often these can
# be called
FLOOD_PREVENTION_INTERVAL_SECONDS = 15

# Maximum number of connections at the same time
MAX_CONCURRENT_API_CONNECTIONS = 10

# We implicitly wait for an image to be in READY state when submitting
# jobs. If this for some reason never happens, error out after this interval
MAX_WAIT_FOR_IMAGE_TRANSITION_PENDING_READY_SECONDS = 5 * 60

# Timeout settings. We set 20 secont timeout delay for connection, and 5 minutes
# for each download.
REQUESTS_TIMEOUTS = (20, 300)
