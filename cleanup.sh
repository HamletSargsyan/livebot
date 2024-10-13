#!/bin/bash

find . -type d -name "__pycache__" -exec rm -rf {} +

rm -rf .*_cache nohup.out .pid site release_body.md
