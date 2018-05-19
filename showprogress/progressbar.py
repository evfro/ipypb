from IPython.display import ProgressBar

PBFORMAT = '''<div>
                <progress style=width:"{width}" max="{total}" value="{value}" class="Progress-main">
                </progress>
                <span class="Progress-label"><strong>{progress:.0f}%</strong></span>
                <span class="Iteration-label">{step}/{total}</span>
              </div>'''


class StyledProgressBar(ProgressBar):
    def __init__(self, iterable, total=None):
        try:
            size = len(iterable)
        except TypeError:
            msg = 'Please provide the `total` argument for total number of iterations.'
            assert isinstance(total, int), msg
            size = total
        super().__init__(size)
        self.exec_time = None
        self._bar = PBFORMAT
        self.step = (size // 100) or 1
        self.step_progress = 0

    def _repr_html_(self):
        total = self.total
        progress = self.progress
        progress_perc = 100 * (progress/total)
        if (progress % self.step) == 0:
            self.step_progress = progress

        config = dict(width=self.html_width,
                      total=total,
                      value=progress,
                      progress=progress_perc,
                      step=self.step_progress)

        return self._bar.format(**config)
