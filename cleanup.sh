#!/bin/bash

find . -type d -name "__pycache__" -exec rm -rf {} +

rm -rf .ruff_cache nohup.out
