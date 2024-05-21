#!/bin/bash

find . -type d -name "__pycache__" -exec rm -rfv {} +

rm -rf .ruff_cache nohup.out .pid site
