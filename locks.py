import threading
import contextlib

class lock():
    def __init__(self):
        self.l = threading.RLock()

    @contextlib.contextmanager
    def locked(self):
        self.l.acquire()
        try:
            yield
        finally:
            self.l.release()

    @contextlib.contextmanager
    def unlocked(self):
        self.l.release()
        try:
            yield
        finally:
            self.l.acquire()
