import pystray
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


icon = pystray.Icon(
    'test name',
    icon=create_image(64, 64, 'black', 'white'))

icon.menu = pystray.Menu(pystray.MenuItem(
    text="Exit",
    action=lambda: icon.stop()
))

icon.run()