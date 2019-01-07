from itertools import takewhile
from operator import length_hint
from timeit import default_timer as timer
from IPython.display import ProgressBar


STD_FILL = '█'

PBFORMAT = ['<progress style=width:"{width}" max="{total}" value="{value}" class="Progress-main"/></progress>',
            '<span class="Progress-label"><strong>{complete:.0f}%</strong></span>',
            '<span class="Iteration-label">{step}/{total}</span>',
            '<span class="Time-label">[{time[0]:.2f}<{time[1]:.2f}, {time[2]:.2f}s/it]</span>']


def exec_time():
    start0 = start = timer()
    yield
    while True:
        stop = timer()
        yield (stop-start, stop-start0)
        start = stop


class ProgressBarInputError(ValueError):
    """Raise on invalid input to progress bar"""

class InteractiveRangeInputError(ValueError):
    """Raise on invalid input to interactive range"""


class ConfigurableProgressBar(ProgressBar):
    def __init__(self, iterable=None, total=0, keep=True, text=None):
        size = total or length_hint(iterable)
        if size == 0: # unable to determine input sequence length
            raise ProgressBarInputError('Please specify the total number of iterations')
        if (size < 0) or not isinstance(size, int):
            raise ProgressBarInputError('The total number of iterations must be an integer value above 0')

        super().__init__(size)
        self.iterator = iter(range(size)) if iterable is None else iter(iterable)
        self.step = (size // 100) or 1
        self.step_progress = 0
        self.time_stats = (0,)*3 # iter. time, total time, time per iter.
        self.exec_time = None
        self.pbformat = PBFORMAT
    def __repr__(self):
        fraction = self.progress / self.total
        complete = STD_FILL * int(fraction * self.text_width)
        return f'[{complete:<{self.text_width}}] {self.progress}/{self.total}'

    def bar_html(self):
        return "\n".join(self.pbformat)

    def _repr_html_(self):
        perc_complete = 100 * (self.progress/self.total)
        if (self.progress % self.step) == 0:
            self.step_progress = self.progress

        config = dict(width=self.html_width,
                      total=self.total,
                      value=self.progress,
                      complete=perc_complete,
                      step=self.step_progress,
                      time=self.time_stats)
        return f'<div>{self.bar_html()}</div>'.format(**config)

    def _check_time(self):
        progress = self._progress
        if progress == -1:
            self.exec_time = exec_time()
            self.exec_time.send(None) # prime timer
        else:
            timings = next(self.exec_time)
            self.time_stats = timings + (timings[1] / (progress+1),)

    def __next__(self):
        """Returns current value and time; increments display by one."""
        self._check_time()
        try:
            super().__next__() # updates display as well
        except StopIteration as e:
            if length_hint(self.iterator) > 0:
                # handle incompatible iterator length
                print('Input sequence is not exhausted.')
            raise e
        return next(self.iterator)


class InteractiveRange(ConfigurableProgressBar):
    def __init__(self, low, high=None, step=None, keep=True, text=None):
        if not isinstance(low, int):
            raise InteractiveRangeInputError("Input must be an integer value")

        if high is None:
            # abuse signature for convenience
            # allow (low, None, None) and even (low, None, step)
            high = low
            low = 0

        if low >= high:
            raise InteractiveRangeInputError("`low` should be lower than `high`")

        iterable = range(*takewhile(lambda x: x is not None, [low, high, step]))
        super().__init__(iterable=iterable, total=None, keep=keep, text=text)
