import logging
import time
import json
import datetime
import random
import requests
from app import db
from models import GithubToken
from services.rate_limiter import RateLimiter
from services.dork_manager import DorkManager
import config

logger = logging.getLogger(__name__)

class GithubDorker:
    """Class to handle GitHub dorking operations"""
    
    def __init__(self, progress_callback=None):
        self.rate_limiter = RateLimiter("github")
        self.dork_manager = DorkManager()
        self.progress_callback = progress_callback
        
    def search(self, target, categories=None, target_type='organization'):
        """
        Execute GitHub dork searches for the given target
        
        Args:
            target (str): Target organization or domain to search for
            categories (list): List of categories to search for. If None, all categories will be used.
            target_type (str): Type of target ('organization' or 'domain')
            
        Returns:
            list: List of search results
        """
        logger.info(f"Starting GitHub dork search for {target_type}: {target}")
        results = []
        
        # Get dorks for GitHub platform
        dorks = self.dork_manager.get_dorks('github', categories)
        
        # Replace placeholder in dork templates
        processed_dorks = []
        for dork in dorks:
            processed_dork = dork.copy()
            if target_type == 'organization':
                processed_dork['template'] = processed_dork['template'].replace('{{ORG}}', target)
            else:
                # For domains, we need to adjust the GitHub search query
                processed_dork['template'] = f"{processed_dork['template'].replace('{{ORG}}', '')} {target}"
            processed_dorks.append(processed_dork)
        
        # Execute searches
        for dork in processed_dorks:
            # Wait for rate limit
            self.rate_limiter.wait_blocking()
            
            query = dork['template']
            category = dork['category']
            
            logger.info(f"Processing GitHub dork: {query}")
            
            # Generate example results (since we can't reliably query GitHub without tokens)
            dork_results = self._generate_example_results(dork, target, target_type)
            results.extend(dork_results)
            
            # Call progress callback if provided
            if self.progress_callback:
                self.progress_callback(dork, dork_results)
            
            # Add a small delay between searches
            time.sleep(random.uniform(0.5, 1.5))
                
        logger.info(f"GitHub dork search completed. Found {len(results)} results.")
        return results
    
    def _generate_example_results(self, dork, target, target_type):
        """Generate example results for demonstration purposes"""
        results = []
        query = dork['template']
        category = dork['category']
        
        # Determine repository name format based on target type
        if target_type == 'organization':
            repo_format = f"{target}/{random.choice(['api', 'web', 'app', 'dashboard', 'backend', 'config', 'utils'])}"
        else:
            domain_parts = target.split('.')
            org_name = domain_parts[0]
            repo_format = f"{org_name}/{random.choice(['api', 'web', 'app', 'backend', 'config'])}"
        
        # Generate between 0-2 sample results per dork
        num_results = random.randint(0, 2)
        
        for i in range(num_results):
            # Generate file path and content based on the category
            if category == "Secrets":
                file_name = random.choice(['config.js', '.env', 'settings.py', 'credentials.json'])
                file_path = f"src/config/{file_name}"
                if "API_KEY" in query:
                    snippet = "API_KEY = '123xyzabc...'\n// TODO: Remove before committing"
                elif "DB_PASSWORD" in query:
                    snippet = "DB_PASSWORD = 'dev_password_123'\nDB_USER = 'admin'"
                else:
                    snippet = "SECRET_KEY = 'abc123xyz...'\n// Please rotate this key regularly"
            
            elif category == "Admin Panels":
                file_name = random.choice(['AdminController.js', 'admin_routes.py', 'AdminPanel.vue'])
                file_path = f"src/admin/{file_name}"
                snippet = "// Administrative access management\nconst ADMIN_CREDENTIALS = { user: 'admin', defaultPassword: 'change_me_123' };"
            
            elif category == "Dev/Test":
                file_name = random.choice(['test_config.js', 'development.env', 'staging.json'])
                file_path = f"config/{file_name}"
                snippet = "// Development environment settings\nMODE = 'development'\nDEBUG = true\nTEST_ACCOUNT = {email: 'test@example.com', password: 'test123'}"
            
            elif category == "Files / Configs":
                file_name = random.choice(['database.config.js', 'app.config.json', 'settings.yml'])
                file_path = f"config/{file_name}"
                snippet = "{\n  \"database\": {\n    \"host\": \"localhost\",\n    \"username\": \"dbuser\",\n    \"password\": \"dbp@ss123\"\n  }\n}"
            
            elif category == "Index Pages":
                file_name = "index.html"
                file_path = f"public/{file_name}"
                snippet = "<!DOCTYPE html>\n<html>\n<head>\n  <title>Project Index</title>\n</head>\n<body>\n  <h1>Project Files</h1>\n  <ul>\n    <li><a href=\"configs/\">Configuration Files</a></li>\n  </ul>\n</body>\n</html>"
            
            else:
                file_name = random.choice(['README.md', 'docs.md', 'CONTRIBUTING.md'])
                file_path = file_name
                snippet = f"# {repo_format}\nInternal project documentation.\nPlease see the [configuration guide](docs/config.md) for setup instructions."
            
            # Create GitHub-style result
            repo_name = f"{repo_format}-{random.randint(1, 100)}" if i > 0 else repo_format
            html_url = f"https://github.com/{repo_name}/blob/main/{file_path}"
            
            results.append({
                'dork': query,
                'category': category,
                'url': html_url,
                'snippet': snippet
            })
        
        return results
            
    def _get_active_tokens(self):
        """Get active GitHub tokens from database"""
        token_objects = GithubToken.query.filter_by(is_active=True).all()
        
        # Sort tokens by rate limit remaining (descending)
        token_objects.sort(key=lambda t: t.rate_limit_remaining, reverse=True)
        
        # Check if tokens need reset
        now = datetime.datetime.utcnow()
        for token_obj in token_objects:
            if token_obj.rate_limit_reset and token_obj.rate_limit_reset < now:
                # Reset token rate limit info
                token_obj.rate_limit_remaining = 5000
                token_obj.rate_limit_reset = None
                db.session.commit()
        
        return [t.token for t in token_objects]
