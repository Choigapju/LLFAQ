from PIL import Image
from pathlib import Path

static_dir = Path("static")
if not static_dir.exists():
    static_dir.mkdir(parents=True)

favicon_path = static_dir / "favicon.ico"

img = Image.new('RGB', (16, 16), color='blue')
img.save(favicon_path, format='ICO')

print(f"Favicon created at: {favicon_path.absolute()}")