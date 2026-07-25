from pathlib import Path
import tomllib


ROOT = Path(__file__).parent

AUTHOR = "Lorenzo Tumini"
SITENAME = "Lorenzo Tumini"
SITESUBTITLE = "Projects and technical notes"
SITEURL = ""

PATH = "content"
OUTPUT_PATH = "output/"
DELETE_OUTPUT_DIRECTORY = True
THEME = str(ROOT / "theme")

TIMEZONE = "Europe/Rome"
DEFAULT_LANG = "en"
DEFAULT_DATE_FORMAT = "%d %B %Y"

ARTICLE_PATHS = ["articles"]
ARTICLE_URL = "articles/{slug}/"
ARTICLE_SAVE_AS = "articles/{slug}/index.html"

# Pages are parsed so the home template can use home.md, but they are not
# emitted as separate files.
PAGE_PATHS = ["pages"]
PAGE_URL = ""
PAGE_SAVE_AS = ""

DIRECT_TEMPLATES = ["index", "archives"]
ARCHIVES_SAVE_AS = "articles/index.html"
AUTHORS_SAVE_AS = ""
CATEGORIES_SAVE_AS = ""
TAGS_SAVE_AS = ""
AUTHOR_SAVE_AS = ""
CATEGORY_SAVE_AS = ""
TAG_SAVE_AS = ""

DEFAULT_PAGINATION = False
RELATIVE_URLS = True

FEED_ALL_ATOM = None
FEED_ALL_RSS = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
CATEGORY_FEED_ATOM = None
CATEGORY_FEED_RSS = None
TRANSLATION_FEED_ATOM = None
TRANSLATION_FEED_RSS = None

MARKDOWN = {
    "extension_configs": {
        "markdown.extensions.extra": {},
        "markdown.extensions.codehilite": {
            "css_class": "highlight",
            "guess_lang": False,
        },
        "markdown.extensions.meta": {},
    },
    "output_format": "html5",
}

with (ROOT / "data" / "projects.toml").open("rb") as project_file:
    PROJECTS = tomllib.load(project_file)["projects"]
