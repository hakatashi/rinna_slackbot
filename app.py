from pystray import Menu, MenuItem, Icon
import subprocess
from PIL import Image
from logging import getLogger, INFO
import sys

logger = getLogger(__name__)
logger.setLevel(INFO)

mode = "CPU"
logger.info(f'mode = {mode}')

stdout_stream = open('stdout.log', mode='ab')
stderr_stream = open('stderr.log', mode='ab')

def start_worker_process(mode: str) -> subprocess.Popen:
    """
    Starts the worker.py subprocess with the given mode.
    """
    command = [
        'poetry',
        'run',
        'python',
        '-u',
        'worker.py',
        mode,
        'Llama',
    ]
    logger.info(f"Starting worker process with command: {' '.join(command)}")
    return subprocess.Popen(
        command,
        stdout=stdout_stream,
        stderr=stderr_stream,
        encoding="utf8",
        universal_newlines=True
    )

worker_process = start_worker_process(mode)

icon = Icon(
    'りんな',
    icon=Image.open('icon.png'))


def exit_worker():
    if worker_process.stdout:
        worker_process.stdout.flush()
    if worker_process.stderr:
        worker_process.stderr.flush()
    worker_process.kill()


def exit_process():
    exit_worker()
    icon.stop()


def mode_switch_action(new_mode):
    global worker_process, mode

    exit_worker()
    mode = new_mode
    worker_process = start_worker_process(mode)

    if new_mode == "CPU":
        icon.menu = Menu(switch_to_gpu_item, exit_item)
    elif new_mode == "GPU":
        icon.menu = Menu(switch_to_cpu_item, exit_item)


switch_to_cpu_item = MenuItem(
    text="Switch to CPU mode",
    action=lambda: mode_switch_action("CPU")
)

switch_to_gpu_item = MenuItem(
    text="Switch to GPU mode",
    action=lambda: mode_switch_action("GPU")
)

exit_item = MenuItem(
    text="Exit",
    action=exit_process
)

icon.menu = Menu(switch_to_gpu_item, exit_item)

icon.run()
