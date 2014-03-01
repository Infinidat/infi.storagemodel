from infi.unittest import TestCase
from mock import patch

# TODO TestCases
# No targets are connected, and rescan will not find any targets
# Target added just with LUN 0
# Target removed just with LUN 0
# Target added with 10 LUNs
# Target removed (with all LUNs)
# Some LUNS were removed
# One target is connected, another target is added, then removed
# One target is connected, another target is added and the first one is removed
# Rescan of three new targets each with three new volumes
