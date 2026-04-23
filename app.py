from pystray import Menu, MenuItem, Icon
import subprocess
from PIL import Image
from logging import Logger, getLogger, INFO, StreamHandler, FileHandler, Formatter
import threading
import time
import psutil
from typing import Optional, Tuple

# Constants
RESTART_DELAY_SECONDS = 3
PROCESS_TERMINATION_TIMEOUT_SECONDS = 5
MONITOR_INTERVAL_SECONDS = 1
LOG_FILE = 'app.log'
STDOUT_LOG_FILE = 'stdout.log'
STDERR_LOG_FILE = 'stderr.log'


def setup_logging() -> Logger:
    """Configure and return the application logger."""
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    # ログのフォーマット設定
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # ファイルハンドラの追加
    file_handler = FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # コンソールハンドラの追加
    console_handler = StreamHandler()
    console_handler.setLevel(INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()

mode = "CPU"
logger.info(f'mode = {mode}')

# Global state
worker_process: Optional[subprocess.Popen] = None
should_restart = True
restart_lock = threading.Lock()
stdout_stream: Optional[object] = None
stderr_stream: Optional[object] = None
icon: Optional[Icon] = None


def initialize_log_streams() -> Tuple[object, object]:
    """
    Initialize and open log streams for worker process output.

    Returns:
        Tuple of (stdout_stream, stderr_stream)
    """
    global stdout_stream, stderr_stream
    stdout_stream = open(STDOUT_LOG_FILE, mode='ab')
    stderr_stream = open(STDERR_LOG_FILE, mode='ab')
    logger.info('Log streams initialized')
    return stdout_stream, stderr_stream


def close_log_streams() -> None:
    """Close the log streams safely."""
    try:
        if stdout_stream:
            stdout_stream.close()
        if stderr_stream:
            stderr_stream.close()
        logger.info('Log streams closed')
    except Exception as e:
        logger.error(f'Error closing streams: {e}')


def terminate_process_tree(process: subprocess.Popen) -> None:
    """
    Terminate a process and all its children/grandchildren.

    Args:
        process: The subprocess.Popen instance to terminate
    """
    try:
        parent = psutil.Process(process.pid)
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
        gone, alive = psutil.wait_procs(
            [parent] + children,
            timeout=PROCESS_TERMINATION_TIMEOUT_SECONDS
        )

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
        process.wait()
        logger.info('Process and all children terminated')

    except psutil.NoSuchProcess:
        logger.warning('Process already terminated')
    except Exception as e:
        logger.error(f'Error terminating process: {e}')


def start_worker_process() -> subprocess.Popen:
    """Start the worker process with current mode settings."""
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


def monitor_worker_process() -> None:
    """Monitor the worker process and restart it if it crashes."""
    global worker_process, should_restart

    while should_restart:
        if worker_process is not None:
            returncode = worker_process.poll()

            if returncode is not None:
                logger.error(f'Worker process exited with code: {returncode}')

                with restart_lock:
                    if should_restart:
                        logger.info(f'Restarting worker process in {RESTART_DELAY_SECONDS} seconds...')
                        time.sleep(RESTART_DELAY_SECONDS)
                        start_worker_process()

        time.sleep(MONITOR_INTERVAL_SECONDS)


def main() -> None:
    """Main entry point for the application."""
    # Initialize log streams
    initialize_log_streams()

    # Start worker process
    start_worker_process()

    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_worker_process, daemon=True)
    monitor_thread.start()

    # Create and run system tray icon
    global icon
    icon = Icon('りんな', icon=Image.open('icon.png'))
    icon.menu = Menu(switch_to_gpu_item, exit_item)
    icon.run()


def exit_worker() -> None:
    """Stop the worker process and disable auto-restart."""
    global should_restart

    logger.info('Stopping worker process...')

    with restart_lock:
        should_restart = False

    if worker_process is not None:
        terminate_process_tree(worker_process)


def exit_process() -> None:
    """Exit the application gracefully."""
    exit_worker()
    close_log_streams()
    icon.stop()


def mode_switch_action(new_mode: str) -> None:
    """
    Switch between CPU and GPU modes.

    Args:
        new_mode: The mode to switch to ('CPU' or 'GPU')
    """
    global worker_process, mode, should_restart

    logger.info(f'Switching to {new_mode} mode')

    with restart_lock:
        should_restart = False

    if worker_process is not None:
        terminate_process_tree(worker_process)

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


if __name__ == '__main__':
    main()
