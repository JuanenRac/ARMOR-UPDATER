"""ARMOR-UPDATER - detects, installs, and manually updates every one of
the A.R.M.O.R. ecosystem's projects on the machine it runs on (the central
server, or a dev machine with the same sibling-directory checkout layout).

pyproject.toml's own `version` field is the real source of truth -
`__version__` below is a mirror that `tools/armor_project_tool.py bump` keeps in sync
with it, kept here (rather than reading it back out of installed package
metadata) so this module has a version to report even before
`pip install -e .` has ever run against a bare checkout.
"""
__version__ = "0.1.5"
