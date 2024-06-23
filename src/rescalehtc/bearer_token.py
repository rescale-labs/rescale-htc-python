from __future__ import annotations
import base64
import json
from .exceptions import HtcException


class BearerToken:
    """
    BearerToken objects hold information about a specific Rescale HTC Bearer
    token, which is a JSON Web Token (JWT).

    Access member variables or helper functions here to use the claims in the
    JWT.
    """

    def __init__(self, header: dict, payload: dict, encoded_token: str):
        self.header: dict = dict(header)
        """
        Header part of the JWT.
        """
        self.payload: dict = dict(payload)
        """
        Payload part of the JWT, containing useful info like user email, expiry time,
        custom claims and more.
        """
        self.encoded_token = encoded_token

    def __repr__(self):
        return f"BearerToken(header: {self.header}, payload: {self.payload}, encoded: {self.encoded_token})"

    def get_user_claims(self) -> dict:
        """
        Get any claims in the JWT that were user defined at the time of job submission.

        In the pure JWT these claims are prefixed by userDefined\_ by Rescale. This function
        removes the prefix and returns only claims as given by the user at job submission time.
        """

        user_claims = {}
        for key, value in self.payload.items():
            if key.startswith("userDefined_"):
                original_key = key.replace("userDefined_", "", 1)
                user_claims[original_key] = value

        return user_claims

# Helper for b64 decode
def _b64_decode(data: str) -> bytes:
    data_to_return = data.encode("utf-8")
    reminder = len(data_to_return) % 4
    # append the needed '=' sign
    if reminder > 0:
        data_to_return += b"=" * (4 - reminder)
    return base64.urlsafe_b64decode(data_to_return)

def token_from_str(data: str) -> BearerToken:
    """
    Create a BearerToken object from a JWT encoded string
    of the form "xxxx.yyyy.zzzzz".

    End users should normally not use this function, instead get the BearerToken
    object by calling :func:`~rescalehtc.htcsession.HtcSession.get_bearer_token`
    on the HtcSession object.
    """
    components = data.split(".")

    if len(components) != 3:
        raise HtcException(
            f"Could not decode token. Expected 3 period separated components, "
            f'found {len(components)}. Raw data: "{data}"'
        )

    # Extract the component. No signature verification here, if
    # we want support for that we should import a proper JWT library.
    header, payload, _ = components

    return BearerToken(
        header=json.loads(_b64_decode(header)),
        payload=json.loads(_b64_decode(payload)),
        encoded_token=data,
    )
