from itertools import takewhile
from weakref import WeakSet
from operator import length_hint
from datetime import timedelta, datetime
from timeit import default_timer as timer
from IPython.display import ProgressBar
from IPython.core.interactiveshell import InteractiveShell


std_fill = '█'
std_rest = '#'

max_label_width_html = '10ex'
max_label_width_text = 10

label_styles = {'display':'inline-block',
                'overflow':'hidden',
                'white-space':'nowrap',
                'text-overflow':'ellipsis',
                'min-width':'{min_label_width}',
                'max-width':max_label_width_html,
                'vertical-align':'middle',
                'text-align':'right'}
label_style_html = '; '.join([f'{k}:{v}' for k, v in label_styles.items()])

pb_html_format = [
  f'<span class="Text-label" style="{label_style_html}">{{label}}</span>',
  '<progress style="width:{width}" max="{total}" value="{value}" class="Progress-main"/></progress>',
  '<span class="Progress-label"><strong>{complete:.0f}%</strong></span>',
  '<span class="Iteration-label">{step}/{total}</span>',
  '<span class="Time-label">[{time[0]}<{time[1]}, {time[2]:.2f}s/it]</span>',
]

pb_text_format = [f'{{label:>{{min_label_width}}.{max_label_width_text}}}',
                  f'[{{complete:{std_rest}<{{width}}}}]',
                  '{step}/{total}',
                  '[{time[0]}<{time[1]}, {time[2]:.2f}s/it]']


def progressbar_formatter(obj, p, cycle):
    if cycle:
        p.text(f'{obj.__class__.__name__}(...)')
    else:
        # "\033[A" is interpreted by terminal as "move the cursor one line up"
        # allows to undo the default end='\n' in print function
        # "\033[B" is interpreted by terminal as "move the cursor one line down"
        to_last_line = ''
        if (obj.count_id == 0) and (obj._progress == obj.total):
            to_last_line = '\033[B' * type(obj)._max_levels
        moveup = '\033[A' * obj.carriage_moveup
        begin = '\033[2K\r'  # overwrite line, start from the beginning
        p.text(f'{moveup}{begin}{repr(obj)}{to_last_line}')


def patch_progressbar_display(cls):
    interactive = InteractiveShell.initialized()
    if interactive: # for ipython terminal
        frm = InteractiveShell.instance().display_formatter.formatters['text/plain']
        frm.for_type(cls, progressbar_formatter) # doesn't affect notebooks
    else: # for pure python in terminal
        # TODO find a way to patch without invoking ipython instance
        pass


def exec_time():
    start0 = start = timer()
    yield
    while True:
        stop = timer()
        yield (stop-start0, stop-start)
        start = stop


def format_time(t):
    delta = timedelta(seconds=t)
    time = datetime.utcfromtimestamp(delta.total_seconds())

    hours = time.hour + delta.days * 24
    minutes = time.minute
    seconds = time.second + round(time.microsecond * 1e-6)
    strtime = '{0:>02}:{1:>02}'.format(minutes, seconds)
    if hours:
        strtime = f'{hours:>02}:{strtime}'
    return strtime


class ProgressBarInputError(ValueError):
    """Raise on invalid input to progress bar"""

class InteractiveRangeInputError(ValueError):
    """Raise on invalid input to interactive range"""


class ConfigurableProgressBar(ProgressBar):
    _instances = WeakSet()
    _depth = 0
    _max_levels = 0

    def __init__(self, iterable=None, total=0, keep=True, label=None):
        size = total or length_hint(iterable)
        if size == 0: # unable to determine input sequence length
            raise ProgressBarInputError('Please specify the total number of iterations')
        if (size < 0) or not isinstance(size, int):
            raise ProgressBarInputError('The total number of iterations must be an integer value above 0')

        super().__init__(size)

        self.iterable = range(size) if iterable is None else iterable
        self.iterator = None
        self.step = (size // 100) or 1
        self.step_progress = 0
        self.time_stats = (0,)*3 # iter. time, total time, time per iter.
        self.exec_time = None
        self.carriage_moveup = 0
        self.label = label or ''

        self.pbformat_html = pb_html_format
        self.pbformat_text = pb_text_format
        self.min_label_width_text = 0
        self.min_label_width_html = 0
        if self.label:
            self.text_width = self.text_width - max_label_width_text
            self.html_width = f'{(int(self.html_width[:-2]) - int(max_label_width_html[:-2]))}ex'
            self.min_label_width_text = max_label_width_text
            self.min_label_width_html = max_label_width_html

        self.count_id = len(type(self)._instances)
        type(self)._max_levels = max(type(self)._max_levels, self.count_id)
        type(self)._instances.add(self)

    def bar_text(self):
        return ' '.join(self.pbformat_text)

    def __repr__(self):
        fraction = self.progress / self.total
        complete = std_fill * int(fraction * self.text_width)
        config = dict(label=self.label,
                      complete=complete,
                      width=self.text_width,
                      step=self.progress,
                      time=self.time_stats,
                      total=self.total,
                      min_label_width=self.min_label_width_text)
        return self.bar_text().format(**config)

    def bar_html(self):
        return '\n'.join(self.pbformat_html)

    def _repr_html_(self):
        perc_complete = 100 * (self.progress/self.total)
        if (self.progress % self.step) == 0:
            self.step_progress = self.progress

        config = dict(width=self.html_width,
                      total=self.total,
                      value=self.progress,
                      complete=perc_complete,
                      step=self.step_progress,
                      time=self.time_stats,
                      label=self.label,
                      min_label_width=self.min_label_width_html)
        return f'<div>{self.bar_html()}</div>'.format(**config)

    def _check_time(self):
        progress = self._progress
        if progress == -1: # has just been initialized with __iter__ method
            self.exec_time = exec_time()
            self.exec_time.send(None) # prime timer
        else:
            timings = next(self.exec_time)
            strtime = tuple([format_time(t) for t in timings])
            self.time_stats = strtime + (timings[1] / (progress+1),)

    def __iter__(self):
        self.carriage_moveup = 0 # allow end='\n' in print function
        super().__iter__() # also initializes display area for progressbar
        self.iterator = iter(self.iterable)
        return self

    def __next__(self):
        """Returns current value and time; increments display by one."""
        self._check_time()
        self.carriage_moveup = 1 + self._depth # move up this amount of lines
        type(self)._depth = 1
        try:
            super().__next__() # updates display as well
        except StopIteration as e:
            if length_hint(self.iterator) > 0:
                # handle incompatible iterator length
                print('Input sequence is not exhausted.')
            raise e
        type(self)._depth = 0
        return next(self.iterator)


patch_progressbar_display(ConfigurableProgressBar)


class InteractiveRange(ConfigurableProgressBar):
    def __init__(self, low, high=None, step=None, keep=True, label=None):
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
        super().__init__(iterable=iterable, total=None, keep=keep, label=label)
