import json
import base64
with open('screenshots/test_v3.json', 'r') as f:
    data = json.load(f)
with open('screenshots/v3_screenshot.png', 'wb') as f:
    f.write(base64.b64decode(data['base64']))
print(f"截图已保存: {data['width']}x{data['height']}")
