#!/bin/bash

python3 -m venv virtual-env
source virtual-env/bin/activate

# pip install handled through manual installation rather than requiements.txt
# due to local files

pip install ./
pip install pytest-asyncio