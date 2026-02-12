import functools
import traceback as tracebk
from typing import Optional
from dash import callback_context, no_update
from . import log

lg = log.get(__name__)

class mkErr(RuntimeError):
	def __init__(self, msg: str, orig: Optional[Exception]=None):
		self.msg = msg
		self.orig = orig

		errMsg = f"{msg}" if not orig else f"{msg}: {str(orig)}"
		super().__init__(errMsg)

		lg.error(errMsg)
		lg.error(tracebk.format_exc())

	@staticmethod
	def wrap(msg: str, e: Exception): return mkErr(msg, e)


def injectCallbacks(app):
	ocb = app.callback

	def newCB(*args, **kwargs):
		fn = ocb(*args, **kwargs)

		def fnOnWarp(func):
			@functools.wraps(func)
			def wrapped_func(*func_args, **func_kwargs):
				try: return func(*func_args, **func_kwargs)
				except Exception as e:
					ctx = callback_context
					trigger = ctx.triggered[0] if ctx.triggered else "Unknown trigger source"

					error_msg = f"[CallBack] ERR: {str(e)}"
					stack_trace = tracebk.format_exc()
					lg.error(f"{error_msg}\nTrigger source: {trigger}\n{stack_trace}")


					return no_update

			return fn(wrapped_func)

		return fnOnWarp

	app.callback = newCB
