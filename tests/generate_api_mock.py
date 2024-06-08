#!/usr/bin/env python3

"""
This file taks as input a JSON spec of the Rescale HTC API, and
populates the autogenerated region of api_flask_mock.py. The spec
is scraped from the HTML of the HTC documentation.
"""

import re
import json

# Load the json document with the API spec
with open("api_spec/api_spec.json") as fp:
    api_spec = json.load(fp)

api_endpoints_src = ""

# Every URL endpoint in the API
for endpoint in api_spec:
    desired_status_code = None # First, TODO

    # Skip the following endpoints from autogenerating:
    #  * auth endpoint, as we need the default examples don't work there, we need
    #    a custom implementation to make the stub work.
    #
    #  * Image status endpoint, as we need the status to return READY instead of PENDING
    if endpoint["url"] in ["/auth/token"]:
        continue
    if endpoint["method"] == "GET" and endpoint["url"] in ["/htc/projects/{projectId}/container-registry/images/{imageName}"]:
        continue

    # Change the URL format to the route format of Flask
    parameterized_url = endpoint["url"].replace("{", "<").replace("}", ">")

    # Make a python friendly function name from the URL
    function_name = f"endpoint_{endpoint['method']}_"+re.sub(r"\W+", "_", endpoint['url'])

    # Figure out what the parameters to the endpoint is
    parameters = [re.sub(r"[{}]", "", item) for item in re.findall(r"{\w+}", endpoint["url"])]

    # Create the sourcecode of the flask endpoint function
    src = f"""

@app.route("{parameterized_url}", methods=["{endpoint['method']}"])
def {function_name}({", ".join(parameters)}):
    target_status = int(os.environ.get('RESCALECTRL_MOCK_TARGET_STATUS', 0))"""

    # If there are responses to this endpoint, add it
    if endpoint["responses"]:
        # There may be multiple different status codes that can be returned
        for i, response in enumerate(endpoint["responses"]):
            src += f"""
    if {"not target_status or " if i == 0 else ""}target_status == {response['status']}:
        """
            # If no payload for a given status code, return empty string and the status code
            if "payload" not in response:
                src += f"""return "", {response['status']}"""
            # Else construct the return object
            else:
                # Looks like json
                if response['payload'].startswith("{") or response['payload'].startswith("["):
                    payload_nolines = f'jsonify(json.loads("""{response["payload"]}"""))'
                # Looks like something else
                else:
                    payload_nolines = "'"+response['payload']+"'"

                src += f"""return ({payload_nolines}, {response['status']} )"""

            # TODO: Support all the status codes
            #break
    # All endpoints need at least one response, generation failure otherwise
    else:
        raise Exception
    # Should never arrive here in the API, should've hit a previous return
    src += """
    raise Exception"""
    api_endpoints_src += src

# Add the generated sourceode into the mock API .py file
with open("api_flask_mock.py") as fp:
    filebuf = ""
    in_autogen_region = False
    for line in fp:
        if not in_autogen_region:
            filebuf += line
        if line.startswith("# START_AUTOGENERATED_API"):
            filebuf += api_endpoints_src
            in_autogen_region = True

        if line.startswith("# END_AUTOGENERATED_API"):
            filebuf += "\n\n# END_AUTOGENERATED_API\n"
            in_autogen_region = False

with open("api_flask_mock.py", "w") as fp:
    fp.write(filebuf)

