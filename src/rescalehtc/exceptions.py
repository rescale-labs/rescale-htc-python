"""
This module holds Exceptions used by the rescalehtc library.

Operations that cause an exception to be raised are:

* Any REST API call with the .api. module that returns HTTP >= 400
* Any unrecoverable errors within the library, like bad input types to functions
* Operations which target an Id and has no other return value to indicate failures

Normal "empty-result" operations like if searching for a list
of tasks by name returns 0 entries will not cause an exception,
but instead return an empty list.

Searches for e.g. tasks by ID like in :func:`rescalehtc.htctasks.get_task_with_id`
returns None if nothing is found.

Delete operations by ID will return None if a task is not deleted
succesfully, like in :func:`rescalehtc.htctasks.delete_task_with_id`.
"""
from __future__ import annotations


class HtcException(Exception):
    """
    Main exception for this library.
    """
    def __init__(self, message, status_code=None):
        super().__init__(message)

        self.status_code = status_code
        """
        If the exception comes as a result of a >=400 HTTP status, code
        then this field holds the status code. Otherwise None.
        """
