#!/bin/bash
set -e

cd crawl/crawl-ref/source
make -j `nproc` CFLAGS="-DLLM_DATA_DUMP=1" 
