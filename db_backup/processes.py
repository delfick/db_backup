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

def non_hanging_process(process, desc, timeout=30):
    """
    Yield (next_chunk, next_error) pairs from a process
    Make sure if the process hangs that it ends up dying
    If the process fails, we raise a FailedToRun exception
    """
    error_output = []
    make_non_blocking(process.stdout)
    make_non_blocking(process.stderr)

    try:
        for _ in until(timeout):
            try:
                next_chunk = process.stdout.read()
            except IOError:
                next_chunk = ""

            try:
                next_error = process.stderr.read()
            except IOError:
                next_error = ""

            error_output.append(next_error)
            yield next_chunk, next_error

            # Stop when the process has stopped and there is no more output to read
            if not next_chunk and not next_error and process.poll() is not None:
                break
    except KeyboardInterrupt:
        log.error("Force stopping the command")
        pass

    if process.poll() is None:
        # Timedout waiting for the process to finish
        log.error("Timed out waiting for the process to finish")
        process.terminate()
        for _ in until(10):
            if process.poll() is not None:
                break

        if process.poll() is None:
            # Ok, force kill it now
            log.error("Seems the process is hanging, sigkilling it now")
            os.kill(process.pid, signal.SIGKILL)

    if process.poll() != 0:
        raise FailedToRun("{0} failed".format(desc), exit_code=process.returncode, stderr='\n'.join(error_output))

def stdout_chunks(command, options, desc):
    """
    Yield chunks from stdout from a process running specified command
    Anything from stderr is logged
    """
    # Make sure the command itself exists
    try:
        process = subprocess.check_call(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        raise NoCommand("It seems you need to install {0} for {1}".format(command, desc))

    # We can assume the command exists, let's do this!
    log.info("Running \"%s %s\"", command, options)
    process = subprocess.Popen(shlex.split("{0} {1}".format(command, options)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for next_chunk, next_error in non_hanging_process(process, desc):
        if next_error:
            for line in next_error.split('\n'):
                log.info("STDERR: %s", line)
        yield next_chunk

