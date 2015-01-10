import sys
from datetime import datetime
import pytz


def total_seconds(td):
	return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def show(*objs):
	begin = '' if '\r' in objs[0] or '\b' in objs[0] else '\n'
	sys.stdout.write(begin)
	for part in objs:
		sys.stdout.write(str(part))
	sys.stdout.flush()

def say(speech):
	show(speech)

progress = ['/','-','\\','|']
def show_progress(i):
	show('\b \b', progress[i % len(progress)])

def show_times(*args):
	import aspects
	begin = datetime.utcnow().replace(tzinfo=pytz.UTC)
	result = yield aspects.proceed(*args)
	end = datetime.utcnow().replace(tzinfo=pytz.UTC)
	say("\t[time consumed: %.2f seconds]\n" % (end - begin).total_seconds())
	yield aspects.return_stop(result)
