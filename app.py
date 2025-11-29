from pystray import Menu, MenuItem, Icon
import subprocess
from PIL import Image
from logging import getLogger, INFO, StreamHandler, FileHandler, Formatter
import threading
import time
import psutil

logger = getLogger(__name__)
logger.setLevel(INFO)

# ログのフォーマット設定
formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ファイルハンドラの追加
file_handler = FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# コンソールハンドラの追加
console_handler = StreamHandler()
console_handler.setLevel(INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

mode = "CPU"
logger.info(f'mode = {mode}')

stdout_stream = open('stdout.log', mode='ab')
stderr_stream = open('stderr.log', mode='ab')

worker_process = None
should_restart = True
restart_lock = threading.Lock()


def start_worker_process():
    global worker_process

    worker_process = subprocess.Popen(
        [
            'C:\\Users\\hakatashi\\AppData\\Roaming\\Python\\Scripts\\poetry.exe',
            'run',
            'python',
            '-u',
            'worker.py',
            mode,
            'Llama',
        ],
        stdout=stdout_stream,
        stderr=stderr_stream
    )
    logger.info(f'Worker process started with PID: {worker_process.pid}')
    return worker_process


def monitor_worker_process():
    global worker_process, should_restart

    while should_restart:
        if worker_process is not None:
            returncode = worker_process.poll()

            if returncode is not None:
                logger.error(f'Worker process exited with code: {returncode}')

                with restart_lock:
                    if should_restart:
                        logger.info('Restarting worker process in 3 seconds...')
                        time.sleep(3)
                        start_worker_process()

        time.sleep(1)


start_worker_process()

monitor_thread = threading.Thread(target=monitor_worker_process, daemon=True)
monitor_thread.start()

icon = Icon(
    'りんな',
    icon=Image.open('icon.png'))


def exit_worker():
    global should_restart

    logger.info('Stopping worker process...')

    with restart_lock:
        should_restart = False

    if worker_process is not None:
        try:
            parent = psutil.Process(worker_process.pid)
            children = parent.children(recursive=True)

            logger.info(f'Found {len(children)} child/grandchild processes')

            # 親プロセスと全ての子プロセスにterminateシグナルを送信
            parent.terminate()
            logger.info(f'Sent terminate signal to parent PID: {parent.pid}')

            for child in children:
                try:
                    child.terminate()
                    logger.info(f'Sent terminate signal to child PID: {child.pid}')
                except psutil.NoSuchProcess:
                    pass

            # 最大5秒間、プロセスの終了を待機
            gone, alive = psutil.wait_procs([parent] + children, timeout=5)

            logger.info(f'{len(gone)} processes terminated gracefully')

            # まだ生きているプロセスを強制終了
            if alive:
                logger.warning(f'{len(alive)} processes did not terminate, forcing kill...')
                for p in alive:
                    try:
                        p.kill()
                        logger.info(f'Killed process PID: {p.pid}')
                    except psutil.NoSuchProcess:
                        pass

            # 最終的な待機
            worker_process.wait()
            logger.info('Worker process and all children terminated')

        except psutil.NoSuchProcess:
            logger.warning('Worker process already terminated')
        except Exception as e:
            logger.error(f'Error terminating worker process: {e}')


def exit_process():
    exit_worker()

    # ストリームをクローズ
    try:
        stdout_stream.close()
        stderr_stream.close()
        logger.info('Log streams closed')
    except Exception as e:
        logger.error(f'Error closing streams: {e}')

    icon.stop()


def mode_switch_action(new_mode):
    global worker_process, mode, should_restart

    logger.info(f'Switching to {new_mode} mode')

    with restart_lock:
        should_restart = False

    if worker_process is not None:
        try:
            parent = psutil.Process(worker_process.pid)
            children = parent.children(recursive=True)

            logger.info(f'Found {len(children)} child/grandchild processes for termination')

            # 親プロセスと全ての子プロセスにterminateシグナルを送信
            parent.terminate()
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass

            # 最大5秒間、プロセスの終了を待機
            gone, alive = psutil.wait_procs([parent] + children, timeout=5)

            # まだ生きているプロセスを強制終了
            if alive:
                logger.warning(f'{len(alive)} processes did not terminate, forcing kill...')
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass

            worker_process.wait()
            logger.info('Previous worker process and all children terminated')

        except psutil.NoSuchProcess:
            logger.warning('Worker process already terminated')
        except Exception as e:
            logger.error(f'Error terminating worker process during mode switch: {e}')

    mode = new_mode

    with restart_lock:
        should_restart = True

    start_worker_process()

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
