
#  settings here

try:
    from settings_local import *
except ImportError:
    print("please set up settings_local.py for this environment")
