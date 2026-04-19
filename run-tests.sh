#!/bin/bash

output=$(uv run pytest $@ 2>&1)
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "$output"
fi