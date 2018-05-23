# showprogress
Python progress bar that uses native ipython functionality. Widget-free. Works even in JupyterLab.

The reason for creating this package is that other progress bars use custom bar objects and/or widget tools, ignoring native `IPython` functionality. This makes them unusable in "clean" environments like JupyterLab.

# Notes
Currently at pre-alpha stage.

Simple usage example:  
```python
from time import sleep
from showprogress import showprogress

for i in showprogress(range(10)):
    sleep(0.1)
```

# Install
Conda and pip packages are yet to come. Currently you can use:  
`pip install git+https://github.com/evfro/showprogress.git`

# Requirements
Python 3.6+ and IPython v.5.6+ excluding v.6.1 and v.6.2
