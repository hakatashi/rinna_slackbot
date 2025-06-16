from pystray import Menu, MenuItem, Icon
import subprocess
from PIL import Image
from logging import getLogger, INFO

logger = getLogger(__name__)
logger.setLevel(INFO)

mode = "CPU"
logger.info(f'mode = {mode}')

stdout_stream = open('stdout.log', mode='ab')
stderr_stream = open('stderr.log', mode='ab')

worker_process = subprocess.Popen(
    [
        'C:\\Windows\\system32\\wsl.exe',
        '-d',
        'Ubuntu',
        '-e',
        'sh',
        '-c',
        f'PATH=~/.asdf/shims:$PATH /home/hakatashi/.local/bin/poetry run python -u worker.py {mode} Llama',
    ],
    stdout=stdout_stream,
    stderr=stderr_stream
)

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

    worker_process = subprocess.Popen(
        [
            'C:\\Windows\\system32\\wsl.exe',
            '-d',
            'Ubuntu',
            '-e',
            'sh',
            '-c',
            f'PATH=~/.asdf/shims:$PATH /home/hakatashi/.local/bin/poetry run python -u worker.py {mode} Llama',
        ],
        stdout=stdout_stream,
        stderr=stderr_stream,
        encoding="utf8",
        universal_newlines=True
    )
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
