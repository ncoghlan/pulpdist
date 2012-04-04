"""Simple size constrained thread pool that blocks when all threads are busy"""

# Based on Python recipe: http://code.activestate.com/recipes/577187/ (r9)
# Posted by Emilio Monti: http://code.activestate.com/recipes/users/4173642/
# Used under MIT License: http://www.opensource.org/licenses/mit-license.php
# Retrieved 3rd April, 2012

# Updates relative to original recipe:
#   - uses the traceback module to print a full traceback for *all* exceptions
#   - uses a PriorityQueue
#   - uses a namedtuple for Task objects (with a leading priority field)
#   - saves references to the workers from the pool
#   - customises the thread identifiers for the worker threads
#   - timeout support when waiting for task completion

from Queue import PriorityQueue
from threading import Thread
from traceback import format_exc
from collections import namedtuple
from time import time
import sys

Task = namedtuple("Task", "priority func args kwds")

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks, name=None):
        Thread.__init__(self, name=name)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            task = self.tasks.get()
            try:
                task.func(*task.args, **task.kwds)
            except:
                header = "Error in {0}:\n".format(self.name)
                tb = format_exc()
                sys.stderr.write(header+tb)
                sys.stderr.flush()
            finally:
                self.tasks.task_done()

class PendingTasks(Exception):
    """Exception thrown if ThreadPool.wait_for_tasks() times out"""

class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads, name="ThreadPool"):
        self.name=name
        self.tasks = PriorityQueue(num_threads)
        self.workers = [self._add_worker(i) for i in range(num_threads)]

    def _add_worker(self, index):
        name = "{0}-Worker-{1}".format(self.name, index)
        return Worker(self.tasks, name)

    def add_task(self, priority, func, *args, **kwds):
        """Add a task to the queue. Blocks if all threads are busy."""
        self.tasks.put(Task(priority, func, args, kwds))

    def _join_with_timeout(self, timeout):
        """Workaround for the fact Queue.join() doesn't support timeouts"""
        tasks = self.tasks
        tasks.all_tasks_done.acquire()
        try:
            endtime = time() + timeout
            while tasks.unfinished_tasks:
                remaining = endtime - time()
                if remaining <= 0.0:
                    raise PendingTasks
                tasks.all_tasks_done.wait(remaining)
        finally:
            tasks.all_tasks_done.release()

    def wait_for_tasks(self, timeout=None):
        """Wait for completion of all the tasks in the queue"""
        if timeout is None:
            self.tasks.join()
        elif timeout < 0:
            raise ValueError("'timeout' must be a positive number")
        else:
            self._join_with_timeout(timeout)
