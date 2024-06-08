#!/usr/bin/env python3

import shutil
import os
import subprocess

eis_dir = os.path.expanduser(f"~/eis")

if not os.path.isdir(eis_dir):
    print(f"Error: Missing eis folder at {eis_dir}")
    exit(1)

eis_docs_dir = f"{eis_dir}/rescalectrl_docs"


if os.path.isdir(eis_docs_dir):
    print(f"Removing existing docs directory {eis_docs_dir}")
    shutil.rmtree(eis_docs_dir)

docs_dir = os.path.dirname(os.path.abspath(__file__)) + "/_build/html"

shutil.copytree(docs_dir, eis_docs_dir)

subprocess.run(f"chmod -R o=u-w {eis_docs_dir}", shell=True, check=True)

print("Done.")

