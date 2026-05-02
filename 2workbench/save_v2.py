#!/usr/bin/env python3
import json
import base64

with open('screenshots/test_v2.json', 'r') as f:
    data = json.load(f)

with open('screenshots/v2_screenshot.png', 'wb') as f:
    f.write(base64.b64decode(data['base64']))

print(f"截图已保存: {data['width']}x{data['height']}")
