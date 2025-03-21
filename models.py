import datetime
from app import db

class Dork(db.Model):
    """Model for dork templates"""
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)  # google or github
    category = db.Column(db.String(100), nullable=False)
    template = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f"<Dork {self.platform}:{self.category}>"

class ScanSession(db.Model):
    """Model for scan sessions"""
    id = db.Column(db.Integer, primary_key=True)
    target = db.Column(db.String(255), nullable=False)  # domain or org
    target_type = db.Column(db.String(50), nullable=False)  # domain or organization
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    platforms = db.Column(db.String(50), nullable=False)  # google, github, or both
    categories = db.Column(db.Text, nullable=True)  # JSON array of selected categories
    error_message = db.Column(db.Text, nullable=True)
    
    results = db.relationship('Result', backref='scan_session', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScanSession {self.id} - {self.target}>"

class Result(db.Model):
    """Model for scan results"""
    id = db.Column(db.Integer, primary_key=True)
    scan_session_id = db.Column(db.Integer, db.ForeignKey('scan_session.id'), nullable=False)
    dork = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # google or github
    category = db.Column(db.String(100), nullable=False)
    result_url = db.Column(db.Text, nullable=False)
    snippet = db.Column(db.Text, nullable=True)
    severity = db.Column(db.String(20), default='medium')  # high, medium, low
    is_false_positive = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Result {self.id} - {self.platform}>"
        
    def to_dict(self):
        """Convert result to dictionary for API responses"""
        return {
            'id': self.id,
            'scan_session_id': self.scan_session_id,
            'dork': self.dork,
            'platform': self.platform,
            'category': self.category,
            'result_url': self.result_url,
            'snippet': self.snippet,
            'severity': self.severity,
            'is_false_positive': self.is_false_positive,
            'notes': self.notes,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class ProxyServer(db.Model):
    """Model for proxy servers"""
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(10), nullable=False, default='http')  # http, https, socks5
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    last_used = db.Column(db.DateTime, nullable=True)
    failure_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<ProxyServer {self.protocol}://{self.address}:{self.port}>"
    
    def get_url(self):
        """Return the full proxy URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.address}:{self.port}"
        return f"{self.protocol}://{self.address}:{self.port}"

class GithubToken(db.Model):
    """Model for GitHub API tokens"""
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(255), nullable=False)
    owner = db.Column(db.String(100), nullable=True)
    rate_limit_remaining = db.Column(db.Integer, default=5000)
    rate_limit_reset = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<GithubToken {self.id} - Owner: {self.owner}>"
