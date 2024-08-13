# Generates a .ankiaddon file for installing
# Just this shell script in python
# mkdir -p src/web
# curl -o src/web/d3_7.js https://cdn.jsdelivr.net/npm/d3@7
# zip -rj Calibrate.ankiaddon src/*

import os
import requests
import zipfile

url = "https://cdn.jsdelivr.net/npm/d3@7"
save_dir = os.path.join("src", "web")
save_path = os.path.join(save_dir, "d3_7.js")

os.makedirs(save_dir, exist_ok=True)

response = requests.get(url)
if response.status_code == 200:
    with open(save_path, 'wb') as file:
        file.write(response.content)
    print(f"File downloaded and saved to {save_path}")
else:
    print(f"Failed to download the file. Status code: {response.status_code}")

zip_filename = "Calibrate.ankiaddon"
src_folder = "src"

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, src_folder)  # Use relative path without the 'src' folder
            zipf.write(file_path, arcname)

print(f"Contents of '{src_folder}' zipped into '{zip_filename}'")
