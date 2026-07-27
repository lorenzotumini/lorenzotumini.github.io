"""Production settings used by the GitHub Pages workflow."""

import os

from pelicanconf import *  # noqa: F403


SITEURL = os.environ["SITEURL"].rstrip("/")
RELATIVE_URLS = False
DELETE_OUTPUT_DIRECTORY = True
