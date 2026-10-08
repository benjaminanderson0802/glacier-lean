"""The vault lock serves waiting threads in arrival order, so a save never starves behind busy readers."""
import threading
import time

import vault


def test_fair_lock_is_reentrant_and_serves_in_arrival_order():
    lock = vault.FairRLock()
    order, started = [], []
    lock.acquire()
    lock.acquire()  # re-entrant
    lock.release()

    def worker(name):
        started.append(name)
        with lock:
            order.append(name)

    threads = []
    for name in ("first", "second", "third"):
        t = threading.Thread(target=worker, args=(name,))
        t.start()
        threads.append(t)
        while name not in started:
            time.sleep(0.001)
        time.sleep(0.05)  # let it queue before the next one arrives
    lock.release()
    for t in threads:
        t.join(5)
    assert order == ["first", "second", "third"]


def test_a_greedy_reader_cannot_starve_a_waiting_writer():
    lock = vault.FairRLock()
    stop, writer_done = threading.Event(), threading.Event()

    def reader():
        while not stop.is_set():
            with lock:
                time.sleep(0.002)

    readers = [threading.Thread(target=reader) for _ in range(4)]
    for t in readers:
        t.start()
    time.sleep(0.05)
    started = time.monotonic()

    def writer():
        with lock:
            writer_done.set()

    threading.Thread(target=writer).start()
    assert writer_done.wait(2), "writer waited too long behind readers"
    assert time.monotonic() - started < 1
    stop.set()
    for t in readers:
        t.join(5)


def test_timeout_gives_up_without_blocking_later_threads():
    lock = vault.FairRLock()
    lock.acquire()
    result = []
    t = threading.Thread(target=lambda: result.append(lock.acquire(timeout=0.05)))
    t.start(); t.join(2)
    assert result == [False]
    lock.release()
    assert lock.acquire(timeout=1)
    lock.release()
