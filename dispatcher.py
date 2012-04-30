
import collections
import pyuv
import spidermonkey
import greenlet


class Mailbox(object):
  def __init__(self, g):
    self._g = g
    self.messages = {}

  def cast(self, pat, msg):
    self.messages.setdefault(
      pat,
      collections.deque()
    ).append(msg)


class Address(object):
  def __init__(self, dispatch, mb):
    self._dispatch = dispatch
    self._mb = mb

  def cast(self, pat, msg):
    self._dispatch.cast(self._mb, pat, msg)


def js_print(*args):
  for x in args:
    print x,
  print


def timeout(timer):
  (dis, g) = timer.data
  dis.schedule(g)


cxs = {}


class Dispatcher(object):
  def __init__(self):
    self._loop = pyuv.Loop.default_loop()
    self.main_greenlet = greenlet.getcurrent()
    self.scheduled = collections.deque()
    self.mailboxen = {}

  def schedule(self, g):
    self.scheduled.append(g)

  def spawn(self, filename):
    def func():
      rt = spidermonkey.Runtime(32768)
      cx = rt.new_context()
      cx.add_global("print", js_print)
      cx.add_global("sleep", sleep)
      cx.add_global("receive", receive)
      result = cx.execute(file(filename).read())
      print "done"
    g = greenlet.greenlet(func)
    self.schedule(g)
    gid = id(g)
    self.mailboxen[gid] = Mailbox(g)
    return Address(self, gid)

  def sleep(self, g, how_long):
    t = pyuv.Timer(self._loop)
    t.data = (self, g)
    t.start(timeout, how_long, False)
    self.main_greenlet.switch()

  def cast(self, gid, pat, msg):
    mb = self.mailboxen.get(gid)
    if mb is not None:
      mb.cast(pat, msg)
      self.scheduled.append(mb._g)

  def loop(self):
    while True:
      numg = len(self.scheduled)

      if numg == 0:
        break

      for x in xrange(numg):
        g = self.scheduled.popleft()
        res = g.switch()
        if res is True:
          print "exit", g

      self._loop.run_once()


def spawn(filename):
  return dis.spawn(filename)


def sleep(how_long):
  g = greenlet.getcurrent()
  dis.sleep(g, how_long)


def receive(pattern):
  g = greenlet.getcurrent()
  gid = id(g)
  mb = dis.mailboxen[gid].messages
  while True:
    if pattern in mb:
      q = mb[pattern]
      r = q.popleft()
      if not len(q):
        del mb[pattern]
      return r
    dis.main_greenlet.switch()
    

dis = Dispatcher()
def fun(x):
  p1 = spawn("pingpong.js")
  p2 = spawn("pingpong.js")
  p1.cast('peer', p2)
  p2.cast('peer', p1)
  p1.cast('ping', x)

for x in xrange(63):
  fun(x * 1000)

dis.loop()
