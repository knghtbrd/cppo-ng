
import sys
import logging
import textwrap

### LOGGING
# *sigh* No clean/simple way to use str.format() type log strings without
# jumping through a few hoops

class Message(object):
	def __init__(self, fmt, args):
		self.fmt = fmt
		self.args = args

	def __str__(self):
		return self.fmt.format(*self.args)

class StyleAdapter(logging.LoggerAdapter):
	def __init__(self, logger, extra=None):
		super(StyleAdapter, self).__init__(logger, extra or {})

	def log(self, level, msg, *args, **kwargs):
		if self.isEnabledFor(level):
			msg, kwargs = self.process(textwrap.dedent(msg), kwargs)
			self.logger._log(level, Message(str(msg), args), (), **kwargs)

log = StyleAdapter(logging.getLogger(__name__))


# Set up our logging facility
_handler = logging.StreamHandler(sys.stdout)
_formatter = logging.Formatter('%(message)s')
_handler.setFormatter(_formatter)
log.logger.addHandler(_handler)
log.setLevel(logging.DEBUG)
