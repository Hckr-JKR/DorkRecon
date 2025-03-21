import logging
import datetime
import random
from app import db
from models import ProxyServer
import config

logger = logging.getLogger(__name__)

class ProxyManager:
    """Class to manage proxy servers for web scraping"""
    
    def __init__(self):
        self.use_proxies = config.USE_PROXIES
        
    def get_next_proxy(self):
        """
        Get the next available proxy server
        
        Returns:
            ProxyServer or None: The next proxy to use, or None if no proxies are available
        """
        if not self.use_proxies:
            return None
        
        # Get active proxies with fewer failures than threshold
        proxies = ProxyServer.query.filter_by(is_active=True) \
            .filter(ProxyServer.failure_count < config.PROXY_THRESHOLD_FAILURES) \
            .all()
        
        if not proxies:
            logger.warning("No active proxies available.")
            return None
        
        # Sort by last used time (oldest first)
        proxies.sort(key=lambda p: p.last_used if p.last_used else datetime.datetime.min)
        
        # Choose one of the three oldest proxies randomly
        proxy_count = min(3, len(proxies))
        selected_proxy = random.choice(proxies[:proxy_count])
        
        # Update last used time
        selected_proxy.last_used = datetime.datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Selected proxy: {selected_proxy.protocol}://{selected_proxy.address}:{selected_proxy.port}")
        return selected_proxy
    
    def mark_proxy_failure(self, proxy):
        """
        Mark a proxy as having failed
        
        Args:
            proxy (ProxyServer): The proxy that failed
        """
        if not proxy:
            return
        
        proxy.failure_count += 1
        
        # Disable proxy if failure count exceeds threshold
        if proxy.failure_count >= config.PROXY_THRESHOLD_FAILURES:
            proxy.is_active = False
            logger.warning(f"Proxy {proxy.address}:{proxy.port} marked as inactive after {proxy.failure_count} failures")
        
        db.session.commit()
    
    def reset_proxy_failures(self):
        """Reset failure count for all proxies"""
        ProxyServer.query.update({ProxyServer.failure_count: 0})
        db.session.commit()
        logger.info("Reset failure count for all proxies")
    
    def add_proxy(self, address, port, protocol='http', username=None, password=None):
        """
        Add a new proxy server
        
        Args:
            address (str): Proxy server address
            port (int): Proxy server port
            protocol (str): Proxy protocol (http, https, socks5)
            username (str): Proxy username (optional)
            password (str): Proxy password (optional)
            
        Returns:
            ProxyServer: The newly created proxy object
        """
        new_proxy = ProxyServer(
            address=address,
            port=port,
            protocol=protocol,
            username=username,
            password=password,
            is_active=True
        )
        db.session.add(new_proxy)
        db.session.commit()
        logger.info(f"Added new proxy: {protocol}://{address}:{port}")
        return new_proxy
