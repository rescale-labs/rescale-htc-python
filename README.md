# rescalehtc: A Python module 

This library contains convenient methods for dealing with Rescale HTC, for batch
container running in the cloud.

To build the module execute the following:

```
> pip3 install build
> python3 -m build --wheel
```

The resulting wheel file (saved in the `dist/` directory) and be installed in
the environment of your project with.

```
> pip3 install rescalehtc-%VERSION%-py3-none-any.whl
```

## Documentation

Documentation source is located in the `docs/` folder, and inline in the Python
code. To build the documentation, execute the following (assuming the `make`
tool is available):

```
> pip3 install ".[dev]" 
> cd docs/
> make html
```

Then open `docs\_build\html\index.html` with your web browser.