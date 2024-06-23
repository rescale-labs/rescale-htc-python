# Define some helper functions for dealing with REST APIs

from __future__ import annotations
import threading
import re
from ..internals.constants import MAX_CONCURRENT_API_CONNECTIONS, REQUESTS_TIMEOUTS
from ..exceptions import HtcException
from ..logger import logger

connections_semaphore = threading.Semaphore(value=MAX_CONCURRENT_API_CONNECTIONS)


# Handle API results, return either json or text and raise on HTTP errors
# On errors, also print the returned text before raising exception
def format_api_result(res, return_json, endpoint):
    if res.status_code >= 400:
        raise HtcException(
            f"{res.request.method} {endpoint} | Req body: {res.request.body} | Response: HTTP {res.status_code}: {res.text}",
            res.status_code,
        )
    if return_json:
        return res.json()
    return res.text


# Wrapper for authenticated GET operation, with pagination support
def api_get(rescale, endpoint, params={}, max_items=None, custom_auth_header=None, return_json=True):
    rescale.reauthenticate_if_needed()
    combined_item_res = []
    base_url_re = re.compile(r"https?:\/\/[^ \/]+")
    remaining_max_items = max_items
    # Support multiple paginated GET operations if the "next" field in the response is set
    while endpoint:
        # If we have a max item count, then adjust the page size accordingly for
        # the last page.
        if "pageSize" in params and max_items:
            if remaining_max_items < params["pageSize"]:
                params["pageSize"] = remaining_max_items
                remaining_max_items -= params["pageSize"]

        connections_semaphore.acquire()
        last_res = rescale.requests_session.get(
            endpoint,
            headers={
                "Authorization":
                    custom_auth_header if custom_auth_header
                    else f"Bearer {rescale.RESCALE_HTC_BEARER_TOKEN}"
            },
            params=params,
            timeout=REQUESTS_TIMEOUTS,
        )
        connections_semaphore.release()

        # Handle errors
        if last_res.status_code >= 400:
            raise HtcException(
                f"{last_res.request.method} {endpoint} | Req body: {last_res.request.body} | Response: HTTP {last_res.status_code}: {last_res.text}",
                last_res.status_code,
            )

        # Only if this is a json response can we look for a "next" field to loop over
        if return_json:
            last_res_json = last_res.json()
            # If there is no "items" key, then just return it immediately. This
            # happens for some API endpoints like auth/token/whoami
            if "items" not in last_res_json:
                return last_res_json
            # If there is an "items" key, then only track that list and return it without
            # the "items" layer. This enables us to more invisibly replace the response here
            # with an async iterator in the future.

            # Combine this result with the buffer so far
            combined_item_res += last_res_json["items"]
            if "next" in last_res_json and (remaining_max_items is None or remaining_max_items > 0):
                # Refuse to be forwarded into pagination on a different base URL
                r = base_url_re.match(endpoint)
                if r:
                    current_base_url = r.group(0)
                else:
                    raise HtcException(
                        f"Base of URL {endpoint} doesn't look like an URL"
                    )
                r = base_url_re.match(endpoint)
                if r:
                    next_base_url = base_url_re.search(last_res_json["next"]).group(0)
                else:
                    raise HtcException(
                        f"Base of URL {endpoint} doesn't look like an URL"
                    )
                if current_base_url != next_base_url:
                    logger.debug(
                        "next field in paginated results point to different domain, stopping pagination"
                    )
                    return combined_item_res

                # Continue to the next page in the result
                endpoint = last_res_json["next"]
            else:
                # Stop GET'ing new pages when there no longer is a "next" field
                break
        else:
            return format_api_result(last_res, return_json, endpoint)

    return combined_item_res


# Wrapper for authenticated POST operation
def api_post(
    rescale, endpoint, payload, params={}, custom_auth_header=None, return_json=True
):
    rescale.reauthenticate_if_needed()
    connections_semaphore.acquire()
    res = rescale.requests_session.post(
        endpoint,
        headers={
            "Authorization":
                custom_auth_header if custom_auth_header
                else f"Bearer {rescale.RESCALE_HTC_BEARER_TOKEN}"
        },
        json=payload,
        params=params,
        timeout=REQUESTS_TIMEOUTS,
    )
    connections_semaphore.release()
    return format_api_result(res, return_json, endpoint)

# Wrapper for authenticated PUT operation
def api_put(
    rescale, endpoint, payload, params={}, custom_auth_header=None, return_json=True
):
    rescale.reauthenticate_if_needed()
    connections_semaphore.acquire()
    res = rescale.requests_session.put(
        endpoint,
        headers={
            "Authorization":
                custom_auth_header if custom_auth_header
                else f"Bearer {rescale.RESCALE_HTC_BEARER_TOKEN}"
        },
        json=payload,
        params=params,
        timeout=REQUESTS_TIMEOUTS,
    )
    connections_semaphore.release()
    return format_api_result(res, return_json, endpoint)

# Wrapper for authenticated PATCH operation
def api_patch(
    rescale, endpoint, payload, params={}, custom_auth_header=None, return_json=True
):
    rescale.reauthenticate_if_needed()
    connections_semaphore.acquire()
    res = rescale.requests_session.patch(
        endpoint,
        headers={
            "Authorization":
                custom_auth_header if custom_auth_header
                else f"Bearer {rescale.RESCALE_HTC_BEARER_TOKEN}"
        },
        json=payload,
        params=params,
        timeout=REQUESTS_TIMEOUTS,
    )
    connections_semaphore.release()
    return format_api_result(res, return_json, endpoint)


# Wrapper for authenticated DELETE operation
def api_delete(rescale, endpoint, params={}, custom_auth_header=None, return_json=True):
    rescale.reauthenticate_if_needed()
    connections_semaphore.acquire()
    res = rescale.requests_session.delete(
        endpoint,
        headers={
            "Authorization":
                custom_auth_header if custom_auth_header
                else f"Bearer {rescale.RESCALE_HTC_BEARER_TOKEN}"
        },
        params=params,
        timeout=REQUESTS_TIMEOUTS,
    )
    connections_semaphore.release()
    return format_api_result(res, return_json, endpoint)
