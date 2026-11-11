"""Known bugs from the improvement plan, written as the *expected* behaviour.

Mark each one ``xfail(strict=True)``: it fails until fixed, and the moment a
fix makes it pass pytest reports XPASS -> error. Then move the test to the
matching test file without the marker, as a regression test.

There are no open known bugs right now. Fixed and moved out of this file:
B1, B3, B5, B6, B8a, B8b (phase 1) and B7, B8c (phase 2).
"""
