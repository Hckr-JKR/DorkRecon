import os

# Application settings
DEBUG = True
SECRET_KEY = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Google dorking settings
GOOGLE_SEARCH_URL = "https://www.google.com/search"
GOOGLE_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}
GOOGLE_RETRY_DELAY = 30  # seconds
GOOGLE_MAX_RETRIES = 3
GOOGLE_RESULTS_PER_PAGE = 10

# GitHub dorking settings
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_DEFAULT_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
}
GITHUB_RETRY_DELAY = 60  # seconds
GITHUB_MAX_RETRIES = 3
GITHUB_DEFAULT_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Proxy settings
USE_PROXIES = False  # Set to True to enable proxy rotation
PROXY_THRESHOLD_FAILURES = 3  # Number of failures before marking a proxy as inactive

# Rate limiter settings
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = {
    "google": 10,  # requests per window
    "github": 30   # requests per window
}

# User agent rotation list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:99.0) Gecko/20100101 Firefox/99.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36 Edg/99.0.1150.30",
]

# Database settings
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dorkrecon.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
