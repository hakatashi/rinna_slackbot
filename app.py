import pystray
import subprocess
from PIL import Image, ImageDraw

def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)

    return image

mode = "GPU"

stdout_stream = open('stdout.log', 'a', encoding='utf-8')
stderr_stream = open('stderr.log', 'a', encoding='utf-8')

p = subprocess.Popen(['python', 'worker.py', 'GPU'], stdout=stdout_stream, stderr=stderr_stream)

icon = pystray.Icon(
    'りんな',
    icon=create_image(64, 64, 'black', 'white'))

def exit_process():
    if p.stdout:
        p.stdout.flush()
    if p.stderr:
        p.stderr.flush()
    p.kill()
    icon.stop()

icon.menu = pystray.Menu(
    pystray.MenuItem(
        text="Switch to CPU mode",
        action=lambda: p.kill()
    ),
    pystray.MenuItem(
        text="Exit",
        action=exit_process
    ),
)

icon.run()