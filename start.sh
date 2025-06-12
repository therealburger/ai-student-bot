#!/bin/bash
exec uvicorn bot:app --host=0.0.0.0 --port=10000
