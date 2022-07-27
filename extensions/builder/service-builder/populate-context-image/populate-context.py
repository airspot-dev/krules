import os.path
import yaml
import sys

source_path = sys.argv[1]
destination = sys.argv[2]

source = yaml.load(open(os.path.join(source_path, "source.yaml"), "r"), Loader=yaml.SafeLoader)

for file in source:
    file_path = file["path"]
    if file_path.startswith("/"):
        file_path = file_path[1:]
    parent = os.path.join(destination, os.path.dirname(file_path))
    os.makedirs(parent, exist_ok=True)
    with open(os.path.join(destination, file_path), "w") as f:
        f.write(file["content"])
