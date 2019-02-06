from functools import reduce, partial
from itertools import takewhile, product, chain
from operator import length_hint, mul
from collections import defaultdict
from bisect import bisect_left
from weakref import WeakSet
from timeit import default_timer as timer
from IPython.display import ProgressBar
from IPython.core.interactiveshell import InteractiveShell


std_fill = '█'
std_rest = '#'

max_label_width_html = '15ex'
max_label_width_text = 15

# handle overlapping labels nicely via CSS
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


def register_text_format(cls):
    interactive = InteractiveShell.initialized()
    if interactive: # for ipython terminal
        text_format = InteractiveShell.instance().display_formatter.formatters['text/plain']
        text_format.for_type(cls, progressbar_formatter) # doesn't affect notebooks
    else: # for pure python in terminal
        # TODO patch without invoking ipython instance
        pass


def progressbar_factory(*args, **kwargs):
    # tqdm compatibility
    desc = kwargs.pop('desc', None)
    leave = kwargs.pop('leave', None)
    if desc is not None:
        kwargs['label'] = desc
    if leave is not None:
        kwargs['keep'] = leave

    if isinstance(args[0], int):
        return InteractiveRange(*args, **kwargs)
    return ConfigurableProgressBar(*args, **kwargs)


def stopwatch():
    start0 = start = timer()
    yield
    while True:
        stop = timer()
        yield (stop-start0, stop-start)
        start = stop


def format_elapsed_time(seconds_total):
    minutes, seconds = divmod(seconds_total, 60)
    hours, minutes = divmod(minutes, 60)

    strtime = '{0:>02.0f}:{1:>02.0f}'.format(minutes, seconds)
    if hours:
        strtime = f'{hours:>02.0f}:{strtime}'
    return strtime


class ProgressBarInputError(ValueError):
    """Raise on invalid input to progress bar"""

class InteractiveRangeInputError(ValueError):
    """Raise on invalid input to interactive range"""


class ConfigurableProgressBar(ProgressBar):
    _instances = WeakSet()
    _depth = 0
    _max_levels = 0

    def __init__(self, iterable=None, total=0, keep=True, cycle=False, label=None):
        size = total or length_hint(iterable)
        if size == 0: # unable to determine input sequence length
            raise ProgressBarInputError('Please specify the total number of iterations')
        if (size < 0) or not isinstance(size, int):
            raise ProgressBarInputError('The total number of iterations must be an integer value above 0')

        super().__init__(size)

        self.iterable = range(size) if iterable is None else iterable
        self.iterator = None
        self.cycle = cycle
        self.step = (size // 100) or 1
        self.step_progress = 0
        self.time_stats = (0,)*3 # iter. time, total time, time per iter.
        self.exec_time = None
        self.carriage_moveup = 0
        self.label = label or ''
        self.last_updated = None
        self.update_interval = 0.1

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
            self.exec_time = stopwatch()
            self.exec_time.send(None) # prime timer
        else:
            timings = next(self.exec_time)
            strtime = tuple([format_elapsed_time(t) for t in timings])
            self.time_stats = strtime + (timings[0] / (progress+1),)

    def __iter__(self):
        if self.cycle and (self.iterator is not None):
            self._progress = -1
            type(self)._depth = 0
        else:
            self.carriage_moveup = 0 # allow end='\n' in print function
            super().__iter__() # also initializes display area for progressbar
            self.last_updated = timer()
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

    def update(self, *args, **kwargs):
        time_delta = timer() - self.last_updated
        # control refresh rate
        if (time_delta >= self.update_interval) or (self._progress == self.total):
            super().update(*args, **kwargs)
            self.last_updated = timer()


register_text_format(ConfigurableProgressBar)


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
        super().__init__(iterable=iterable, keep=keep, label=label)


def flatten_dict(schema, parent_key=None, grand_keys=None):
    items = []
    for k, v in schema.items():
        if isinstance(v, dict):
            grand_keys = grand_keys + [parent_key] if parent_key is not None else []
            items.extend(flatten_dict(v, k, grand_keys))
        else:
            prev_keys = tuple(grand_keys) if grand_keys is not None else ()
            prev_keys = prev_keys + (parent_key,) if parent_key is not None else ()
            items.append(prev_keys + (k, v))
    return items

def enumerate_keys_sorted(d):
    return dict(zip(sorted(d.keys()),
                    range(len(d))))

def calculate_joint_size(iterables):
    return reduce(mul, [len(itr) for itr in iterables], 1)

class IterChainTree(dict):
    '''Autovivification process for tree generation'''
    def __init__(self, level, iter_factory, *, parent=None, path=()):
        super().__init__()
        self.parent = parent
        self.path = path
        self.level = level
        self.iter_factory = iter_factory

    def __getitem__(self, key):
        if key == self.level: # handle head iter
            return self # assumed to be already initialized
        return super().__getitem__(key)

    def __missing__(self, key):
        label = key[0]
        path = self.path
        if path: # initialize parent iter (if not head)
            self.iter_factory(path, label)
        next_path = path + (label, len(self))
        iter_chain = self[key] = type(self)(key, self.iter_factory,
                                            parent=self, path=next_path)
        return iter_chain

    def traverse(self, keys, loc=0):
        return self[keys[loc]].traverse(keys, loc+1) if loc < len(keys) else self


class ConfigurableProgressChain(ConfigurableProgressBar):
    def __init__(self, schema, data, *args, transform=None, labels=None, **kwargs):
        self.chain_data = data
        iterable = kwargs.get('iterable', None)
        total = kwargs.get('total', None)
        if iterable is None and total is None:
            iterables = self.chain_data.values()
            kwargs['iterable'] = product(*iterables)
            kwargs['total'] = calculate_joint_size(iterables)

        super().__init__(*args, **kwargs)

        self.label = 'overall'
        self.transform = transform
        self.schema = schema
        self.iter_order = flatten_dict(schema)
        self.iter_index = enumerate_keys_sorted(data)
        self.iter_total = {k: len(v) for k, v in data.items()}
        self.iter_label = labels
        self.iter_trees = None
        self.iter_proxy = None
        self.iter_stage = None
        self.iter_queue = None
        self.display_array = None

    def __iter__(self):
        self.display_array = []
        self.iter_queue = []
        self.iter_stage = set()
        self.iter_proxy = defaultdict(dict) # {line: {path: bar}}
        self.iter_trees = {line: IterChainTree(labels[0],
                                               partial(self.iter_factory,
                                                       self.iter_proxy[line]))
                           for line, labels in enumerate(self.iter_order)}
        super().__iter__()
        self.chain_iter()
        return self

    def iter_factory(self, proxy, path, label):
        try:
            proxy[path]
        except KeyError:
            proxy[path] = prog_bar = self.iter_init(label, path)
            self.ensure_display_order(proxy, path)
            # on next iter may loose control due to new param group -> callback
            self.delayed_progress(prog_bar)

    def iter_init(self, label, path):
        try:
            display_label = self.iter_label[label]
        except: # sholdn't break on display issues
            display_label = label
        if len(path)>1:
            level = path[-1]
            display_label = f'{display_label}:{level}'
        return iter(InteractiveRange(self.iter_total[label], label=display_label))

    def ensure_display_order(self, proxy, path):
        if not isinstance(path, tuple): # leave head untouched
            return
        displays = self.display_array
        displays.append(proxy[path]._display_id)
        queue = self.iter_queue
        loc = bisect_left(queue, path) # fast
        if loc < len(queue): # shift displays
            proxy[path]._display_id = displays[loc]
            queue.insert(loc, path) # slow
            for i in range(loc+1, len(displays)):
                prog_bar = proxy[queue[i]]
                prog_bar._display_id = displays[i]
                self.iter_stage.add(prog_bar)
        else:
            queue.append(path)

    def delayed_progress(self, prog_bar):
        prog_bar._progress += 1
        self.iter_stage.add(prog_bar)

    def chain_iter(self):
        for line, labels in enumerate(self.iter_order):
            iter_proxy = self.iter_proxy[line]
            keys = self.generate_keys(labels, [0]*len(labels))
            for loc, label in enumerate(labels):
                key_path = tuple(chain(*keys[:loc])) if (loc > 0) else label
                self.iter_factory(iter_proxy, key_path, label)

    def generate_keys(self, labels, params):
        keys = (params[self.iter_index[label]] for label in labels)
        return tuple(zip(labels, keys))

    def __next__(self):
        self.update_staged()
        params = super().__next__()
        if self.transform is not None:
            params = self.transform(params)
        self.chain_next(params)
        return params

    def update_staged(self):
        try:
            for prog_bar in self.iter_stage:
                prog_bar.update()
        finally:
            self.iter_stage.clear()

    def chain_next(self, params):
        for line, labels in enumerate(self.iter_order):
            keys = self.generate_keys(labels, params)
            iter_child = self.iter_trees[line].traverse(keys)
            iter_proxy = self.iter_proxy[line]
            self.iter_next(iter_proxy, iter_child.parent)

    def iter_next(self, proxy, tree):
        if tree is None: # return control to main loop
            return
        path = tree.path or tree.level
        prog_bar = proxy[path]
        self.delayed_progress(prog_bar)
        if prog_bar._progress == prog_bar.total: # a la StopIteration
            self.iter_next(proxy, tree.parent)
