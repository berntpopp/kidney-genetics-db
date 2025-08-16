#!/usr/bin/env python3
"""Show status of all data sources"""

import json
import sys

try:
    data = json.load(sys.stdin)
    for source in data:
        status = source['status']
        if status == 'completed':
            color = '\033[92m'  # Green
        elif status == 'running':
            color = '\033[93m'  # Yellow
        elif status == 'failed':
            color = '\033[91m'  # Red
        else:
            color = '\033[0m'   # Default
        
        name = source['source_name']
        pct = source['progress_percentage']
        op = source.get('current_operation', '')
        
        print(f"{color}{name:20} {status:10} {pct:6.1f}%\033[0m  {op}")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)