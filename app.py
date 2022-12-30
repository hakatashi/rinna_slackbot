from pystray import Menu, MenuItem, Icon
import subprocess
from PIL import Image

mode = "GPU"

stdout_stream = open('stdout.log', 'a', encoding='utf-8')
stderr_stream = open('stderr.log', 'a', encoding='utf-8')

worker_process = subprocess.Popen(
    ['python', '-u', 'worker.py', mode],
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
        ['python', '-u', 'worker.py', mode],
        stdout=stdout_stream,
        stderr=stderr_stream
    )
    icon.menu = Menu(switch_to_gpu_item, exit_item)

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

icon.menu = Menu(switch_to_cpu_item, exit_item)

icon.run()