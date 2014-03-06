from contextlib import contextmanager
import subprocess
import logging
import signal
import shlex
import fcntl
import time
import os

from db_backup.errors import NoCommand, FailedToRun

log = logging.getLogger("db_backup")

def until(timeout, step=0.1):
    """Keep yielding until timeout"""
    start = time.time()
    yield
    while time.time() - start < timeout:
        yield
        time.sleep(step)

def make_non_blocking(stream):
    """Make a stream non blocking when you read from it"""
    fd = stream.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def start_process(command, capture_stdin=False, capture_stdout=False, capture_stderr=False):
    stdin = subprocess.PIPE if capture_stdin else None
    stdout = subprocess.PIPE if capture_stdout else None
    stderr = subprocess.PIPE if capture_stderr else None
    return subprocess.Popen(shlex.split(command), stdin=stdin, stdout=stdout, stderr=stderr)

def feed_process(process, desc, food):
    """Feed the stdin of a process"""
    with ensure_killed(process, desc):
        for bite in food:
            if process.poll() is not None:
                break

            process.stdin.write(bite)

        # Finish feeding, close it's mouth
        process.stdin.close()
        wait_for(process, desc, timeout=10)

def check_for_command(command, desc):
    """Raise NoCommand if the specified command doesn't exist"""
    try:
        subprocess.check_call(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        raise NoCommand("It seems you need to install {0} for {1}".format(command, desc))

def wait_for(process, desc, timeout=10, silent=False):
    """
    Wait for a command to finish
    Break early if it finishes
    Just log if it doesn't within the timeout
    It's up to the caller to see if it actually finished
    """
    # And wait for it to finish
    for _ in until(timeout):
        if process.poll() is not None:
            break

    if not silent and process.poll() is None:
        log.error("Timed out waiting for the process to finish (%s)", desc)

@contextmanager
def ensure_killed(process, desc):
    """Make sure the process gets killed"""
    try:
        yield
    except KeyboardInterrupt:
        log.error("Force stopping the process")

    if process.poll() is None:
        # Timedout waiting for the process to finish
        process.terminate()
        wait_for(process, desc, timeout=10, silent=True)

        if process.poll() is None:
            # Ok, force kill it now
            log.error("Seems the process is hanging, sigkilling it now")
            os.kill(process.pid, signal.SIGKILL)

    if process.poll() != 0:
        raise FailedToRun("{0} failed".format(desc), exit_code=process.returncode)

def non_hanging_process(process, desc, timeout=30):
    """
    Yield (next_chunk, next_error) pairs from a process
    Make sure if the process hangs that it ends up dying
    If the process fails, we raise a FailedToRun exception
    """
    make_non_blocking(process.stdout)
    make_non_blocking(process.stderr)

    with ensure_killed(process, desc):
        for _ in until(timeout):
            try:
                next_chunk = process.stdout.read()
            except IOError:
                next_chunk = ""

            try:
                next_error = process.stderr.read()
            except IOError:
                next_error = ""

            yield next_chunk, next_error

            # Stop when the process has stopped and there is no more output to read
            if not next_chunk and not next_error and process.poll() is not None:
                break

        wait_for(process, desc, timeout=0)

def stdout_chunks(command, options, desc):
    """
    Yield chunks from stdout from a process running specified command
    Anything from stderr is logged
    """
    # Make sure the command itself exists
    check_for_command(command, desc)

    # We can assume the command exists, let's do this!
    log.info("Running \"%s %s\"", command, options)
    process = start_process("{0} {1}".format(command, options), capture_stdout=True, capture_stderr=True)

    for next_chunk, next_error in non_hanging_process(process, desc):
        if next_error:
            for line in next_error.split('\n'):
                log.info("STDERR: %s", line)
        yield next_chunk

