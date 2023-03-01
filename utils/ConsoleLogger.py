import os
import io
import sys
from contextlib import redirect_stdout
from contextlib import redirect_stderr

class ConsoleLogger:
  def __init__(self, debug):
    self.suppress_stdout = not debug
    self.suppress_stderr = not debug
    self._stdout = None
    self._stderr = None

  def __enter__(self):
    devnull = open(os.devnull, "w")
    if self.suppress_stdout:
      self._stdout = sys.stdout
      sys.stdout = devnull

    if self.suppress_stderr:
      self._stderr = sys.stderr
      sys.stderr = devnull

  def __exit__(self, *args):
    if self.suppress_stdout:
      sys.stdout = self._stdout
    if self.suppress_stderr:
      sys.stderr = self._stderr

  def info(self, message):
    if not self.suppress_stdout:
      print(message)

  def debug(self, message):
    if not self.suppress_stderr:
      print(message)  

  def output_interceptor(self, func):
    # Decorator for stdout and stderr outputs intecept and parsing
    def wrap(*args, **kwargs):
      stdout = io.StringIO()
      stderr = io.StringIO()
      with redirect_stdout(stdout), redirect_stderr(stderr):
        result = func(*args, **kwargs)
      if not self.suppress_stderr and stderr.getvalue():
        print('\n\n')
        print(stderr.getvalue())
      if not self.suppress_stdout and stdout.getvalue():
        print('\n\n')
        print(stdout.getvalue())
      return result
    return wrap
