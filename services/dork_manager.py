import json
import logging
import os
from app import db
from models import Dork

logger = logging.getLogger(__name__)

class DorkManager:
    """Class to manage dork templates"""
    
    def __init__(self):
        self.dorks = None
        self._load_dorks()
    
    def _load_dorks(self):
        """Load dork templates from database or initialize from JSON file"""
        # Check if dorks are already in the database
        if Dork.query.count() == 0:
            self._initialize_dorks_from_file()
        
    def _initialize_dorks_from_file(self):
        """Initialize dork database from JSON file"""
        try:
            # Load dorks from JSON file
            dork_file_path = os.path.join('data', 'dork_templates.json')
            
            if os.path.exists(dork_file_path):
                with open(dork_file_path, 'r') as f:
                    dork_data = json.load(f)
                
                # Add Google dorks to database
                for dork in dork_data.get('google', []):
                    new_dork = Dork(
                        platform='google',
                        category=dork.get('category'),
                        template=dork.get('template')
                    )
                    db.session.add(new_dork)
                
                # Add GitHub dorks to database
                for dork in dork_data.get('github', []):
                    new_dork = Dork(
                        platform='github',
                        category=dork.get('category'),
                        template=dork.get('template')
                    )
                    db.session.add(new_dork)
                
                db.session.commit()
                logger.info(f"Initialized dork database with {len(dork_data.get('google', []))} Google dorks and {len(dork_data.get('github', []))} GitHub dorks")
            else:
                logger.warning(f"Dork template file not found at {dork_file_path}")
                self._create_default_dorks()
                
        except Exception as e:
            logger.error(f"Error initializing dork database: {str(e)}")
            # Create some default dorks
            self._create_default_dorks()
    
    def _create_default_dorks(self):
        """Create default dorks if JSON file is not available"""
        default_dorks = {
            'google': [
                {'category': 'Secrets', 'template': 'site:{{DOMAIN}} intext:"DB_PASSWORD"'},
                {'category': 'Secrets', 'template': 'site:{{DOMAIN}} intext:"AWS_SECRET_ACCESS_KEY"'},
                {'category': 'Admin Panels', 'template': 'site:{{DOMAIN}} inurl:admin | inurl:login | inurl:dashboard'},
                {'category': 'Files / Configs', 'template': 'site:{{DOMAIN}} ext:env | ext:yml | ext:conf | ext:cfg | ext:ini'}
            ],
            'github': [
                {'category': 'Secrets', 'template': 'org:{{ORG}} AWS_SECRET_ACCESS_KEY'},
                {'category': 'Secrets', 'template': 'org:{{ORG}} password filename:.env'},
                {'category': 'Files / Configs', 'template': 'org:{{ORG}} filename:config.json'},
                {'category': 'Dev/Test', 'template': 'org:{{ORG}} filename:docker-compose.yml'}
            ]
        }
        
        # Add Google dorks to database
        for dork in default_dorks['google']:
            new_dork = Dork(
                platform='google',
                category=dork['category'],
                template=dork['template']
            )
            db.session.add(new_dork)
        
        # Add GitHub dorks to database
        for dork in default_dorks['github']:
            new_dork = Dork(
                platform='github',
                category=dork['category'],
                template=dork['template']
            )
            db.session.add(new_dork)
        
        db.session.commit()
        logger.info("Created default dorks in database")
    
    def get_dorks(self, platform='both', categories=None):
        """
        Get dorks from database
        
        Args:
            platform (str): 'google', 'github', or 'both'
            categories (list): List of categories to filter. If None, all categories will be returned.
            
        Returns:
            list: List of dork dictionaries
        """
        query = Dork.query
        
        # Filter by platform
        if platform != 'both':
            query = query.filter_by(platform=platform)
        
        # Filter by categories
        if categories and len(categories) > 0:
            query = query.filter(Dork.category.in_(categories))
        
        # Get dorks from database
        dork_objects = query.all()
        
        # Convert to dictionaries
        dorks = []
        for dork in dork_objects:
            dorks.append({
                'platform': dork.platform,
                'category': dork.category,
                'template': dork.template
            })
        
        return dorks
    
    def get_categories(self, platform='both'):
        """
        Get unique categories from database
        
        Args:
            platform (str): 'google', 'github', or 'both'
            
        Returns:
            list: List of unique categories
        """
        query = db.session.query(Dork.category).distinct()
        
        # Filter by platform
        if platform != 'both':
            query = query.filter_by(platform=platform)
        
        # Get categories
        categories = [row[0] for row in query.all()]
        return sorted(categories)
    
    def add_dork(self, platform, category, template):
        """
        Add a new dork to the database
        
        Args:
            platform (str): 'google' or 'github'
            category (str): Dork category
            template (str): Dork template string
            
        Returns:
            Dork: The newly created dork object
        """
        new_dork = Dork(
            platform=platform,
            category=category,
            template=template
        )
        db.session.add(new_dork)
        db.session.commit()
        return new_dork
