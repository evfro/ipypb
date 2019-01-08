# Interactive ProgressBar
Python progress bar that uses native ipython functionality. Widget-free. Works even in JupyterLab.

The reason for creating this package is that other progress bars use custom bar objects and/or widget tools, ignoring the builtin `IPython` functionality. This makes them unusable in "clean" environments like JupyterLab. In contrast, `ipynb` can run even in very restricted environments.

Another useful feature of `ipypb` is that the progress bar information is available even after closing a notebook and killing its ipython kernel. Once you launch this notebook again, you'll see the same progress bar information as before closing instead of widjet-related erorrs like `Failed to display Jupyter Widget of type HBox`.

# Notes
Currently at beta stage.

Simple usage example:
```python
from time import sleep
from ipypb import track

for i in track(range(10)):
    sleep(0.1)
```
A few other conveniences are available. For example, you can use `ipypb` as a python's range-like function:
```python
from ipypb import irange

for i in irange(1, 10, 2): # same as range(1, 10, 2) but with progressbar
    # <do stuff>
    ...
```
It may also be helpful to use the factory method `ipb`, which handles different usage scenarios and returns either `track` or `irange` instance depending on input arguments. Another usage example is when you already have a bunch of code with [`tqdm`](https://github.com/tqdm/tqdm) and want to 
replace it with `ipypb`:
```python
from ipypb import ipb

tqdm_notebook = ipb
# or if you run it in interactive shell
tqdm = ipb
```
It will automatically process keyword arguments to ensure compatibility with `tqdm`'s API. Note, that `ipb` offers a common interface for both notebook and terminal environments.

# Install
`pip install ipypb`

# Requirements
Python 3.6+ and IPython v.5.6+ excluding v.6.1 and v.6.2

# Limitations
- The feature to erase progressbar when loop is over is not yet supported.
- Hasn't been tested yet in multithread and multiprocessor environemnts.
