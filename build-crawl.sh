#!/bin/bash
set -e

# Reset and clean the repository
cd crawl/crawl-ref/source
git reset --hard

# Apply all patch files
cp -r ../../../crawl-patches/* .
git apply *.llm-patch
rm -rf *.llm-patch

# Build the game
make -j `nproc` CFLAGS="-DLLM_DATA_DUMP=1" 

# Reset the repository to the upstream state to avoid polluting `git status`
git add -A
git reset --hard
