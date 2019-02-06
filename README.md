# Interactive ProgressBar
Python progress bar that uses native ipython functionality. Widget-free. Works even in JupyterLab.

The reason for creating this package is that other progress bars use custom bar objects and/or widget tools, ignoring the builtin `IPython` functionality. This makes them unusable in "clean" environments like JupyterLab. In contrast, `ipypb` can run even in very restricted environments.

Another useful feature of `ipypb` is that the progress bar information is available even after closing a notebook and killing its ipython kernel. Once you launch this notebook again, you'll see the same progress bar information as before closing instead of widjet-related erorrs like `Failed to display Jupyter Widget of type HBox`, as shown below:

![tqdm - display failure](https://user-images.githubusercontent.com/5283394/52354932-66a7ec80-2a42-11e9-9c10-d314c2bb2f5f.png)

Also have a look at this [NBViewer example](https://nbviewer.jupyter.org/github/evfro/ipypb/blob/master/examples/Usage%20examples.ipynb).

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

## Asynchronous flow
It's also possible to use `ipypb` for tracking tasks that are executed asyncrhonously or in parallel. The major use case is when the order of executed tasks from a task pool doesn't correspond to the desired order for displaying a progress. In this case, you can instruct `ipypb` to preserve the desired order by submitting a description of the progress hierarchy. Below is an example for simple heirarchy consisting of three levels: `i <-- j <-- k`. Progress on each parent level depends on full exectunion of its sublevels. Note how levels `k:1` and `k:2` get moved to the group `j:0` they belong to, even though initially they appear in the end, below the `j:1` group:

![ipypb - async flow](https://user-images.githubusercontent.com/5283394/52353228-26933a80-2a3f-11e9-927a-6bd114f87abe.gif)

**Note**: this feature is currently in provisional state, which means that its API main change in future releases. In order to test it, do 
```python
from ipypb import chain
```

# Install
`pip install --upgrade ipypb`

# Requirements
Python 3.6+ and IPython v.5.6+ excluding v.6.1 and v.6.2

# Limitations
- The feature to erase progressbar when loop is over is not yet supported.
