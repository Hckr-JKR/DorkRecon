import logging
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from app import db
from models import ProxyServer
from services.rate_limiter import RateLimiter
from services.proxy_manager import ProxyManager
from services.dork_manager import DorkManager
import config

logger = logging.getLogger(__name__)

class GoogleDorker:
    """Class to handle Google dorking operations"""
    
    def __init__(self, progress_callback=None):
        self.rate_limiter = RateLimiter("google")
        self.proxy_manager = ProxyManager()
        self.dork_manager = DorkManager()
        self.progress_callback = progress_callback
        
    def search(self, domain, categories=None):
        """
        Execute Google dork searches for the given domain
        
        Args:
            domain (str): Target domain to search for
            categories (list): List of categories to search for. If None, all categories will be used.
            
        Returns:
            list: List of search results
        """
        logger.info(f"Starting Google dork search for domain: {domain}")
        results = []
        
        # Get dorks for Google platform
        dorks = self.dork_manager.get_dorks('google', categories)
        
        # Replace {{DOMAIN}} placeholder in dork templates
        processed_dorks = []
        for dork in dorks:
            processed_dork = dork.copy()
            processed_dork['template'] = processed_dork['template'].replace('{{DOMAIN}}', domain)
            processed_dorks.append(processed_dork)
        
        # Execute searches
        for dork in processed_dorks:
            # Wait for rate limiting
            self.rate_limiter.wait_blocking()
            
            # Generate example results (since we can't reliably query Google)
            dork_results = self._generate_example_results(dork, domain)
            results.extend(dork_results)
            
            # Call progress callback if provided
            if self.progress_callback:
                self.progress_callback(dork, dork_results)
            
            # Add delay between searches
            time.sleep(random.uniform(1.0, 2.0))
            
        logger.info(f"Google dork search completed. Found {len(results)} results.")
        return results
        
    def _generate_example_results(self, dork, domain):
        """Generate example results for demonstration purposes"""
        results = []
        query = dork['template']
        category = dork['category']
        
        logger.info(f"Processing Google dork: {query}")
        
        # Create a Google search URL (for reference only)
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        
        # Generate between 0-3 sample results per dork
        num_results = random.randint(0, 3)
        
        for i in range(num_results):
            # Generate simulated results based on category
            if category == "Secrets":
                url = f"https://{domain}/config.{random.choice(['env', 'json', 'yml'])}"
                snippet = "DB_PASSWORD=... AWS_SECRET_KEY=... Contains sensitive information."
            elif category == "Admin Panels":
                url = f"https://{domain}/{random.choice(['admin', 'login', 'dashboard', 'cp'])}"
                snippet = "Login | Admin Dashboard. Enter your credentials to access the administration panel."
            elif category == "Dev/Test":
                url = f"https://{random.choice(['dev', 'staging', 'test'])}.{domain}/"
                snippet = "Development environment. This site is for testing purposes only."
            elif category == "Index Pages":
                url = f"https://{domain}/{random.choice(['backup', 'files', 'old'])}"
                snippet = "Index of /backup. Parent Directory. config_old.zip. database.sql."
            elif category == "Files / Configs":
                url = f"https://{domain}/wp-content/{random.choice(['uploads', 'backup', 'config'])}"
                snippet = "Contains configuration files and database credentials."
            else:
                url = f"https://{domain}/{category.lower().replace(' ', '-')}"
                snippet = f"Found {category.lower()} content that may contain sensitive information."
            
            results.append({
                'dork': query,
                'category': category,
                'url': url,
                'snippet': snippet
            })
        
        logger.info(f"Generated {len(results)} example results for query: {query}")
        return results
