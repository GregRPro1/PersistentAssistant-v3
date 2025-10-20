#!/usr/bin/env python3
import sys, urllib.request
url = sys.argv[1]
req = urllib.request.Request(url, method="POST")
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.status)
