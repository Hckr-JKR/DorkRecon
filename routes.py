import json
import datetime
from flask import render_template, request, jsonify, redirect, url_for, flash
from app import app, db
from models import Dork, Result, ScanSession, ProxyServer, GithubToken
from services.dork_manager import DorkManager
from services.google_dorker import GoogleDorker
from services.github_dorker import GithubDorker

# Initialize services
dork_manager = DorkManager()

@app.route('/')
def index():
    """Render the main landing page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the dashboard page"""
    # Get recent scan sessions
    recent_sessions = ScanSession.query.order_by(ScanSession.created_at.desc()).limit(10).all()
    return render_template('dashboard.html', recent_sessions=recent_sessions)

@app.route('/settings')
def settings():
    """Render the settings page"""
    # Get proxies and GitHub tokens
    proxies = ProxyServer.query.all()
    tokens = GithubToken.query.all()
    return render_template('settings.html', proxies=proxies, tokens=tokens)

import threading

# Dictionary to store scan progress information
scan_progress = {}

@app.route('/api/scan', methods=['POST'])
def start_scan():
    """API endpoint to start a new scan"""
    data = request.json
    
    # Create a new scan session
    target = data.get('target', '').strip()
    platforms = data.get('platforms', 'both')
    categories = json.dumps(data.get('categories', []))
    target_type = 'domain' if '.' in target else 'organization'
    
    if not target:
        return jsonify({"error": "Target is required"}), 400
    
    new_session = ScanSession(
        target=target,
        target_type=target_type,
        status='pending',
        platforms=platforms,
        categories=categories
    )
    db.session.add(new_session)
    db.session.commit()
    
    # Initialize progress tracking for this session
    scan_progress[new_session.id] = {
        'status': 'initializing',
        'progress': 0,
        'current_step': 'Starting scan...',
        'total_steps': 0,
        'completed_steps': 0,
        'google_dorks_total': 0,
        'google_dorks_completed': 0,
        'github_dorks_total': 0,
        'github_dorks_completed': 0
    }
    
    # Update session status to running
    new_session.status = 'running'
    db.session.commit()
    
    # Start scan in background thread
    scan_thread = threading.Thread(
        target=execute_scan,
        args=(new_session.id, target, platforms, categories, target_type)
    )
    scan_thread.daemon = True
    scan_thread.start()
    
    return jsonify({
        "session_id": new_session.id, 
        "status": "started",
        "message": "Scan started in background. Check progress via /api/scan/progress endpoint."
    })

def execute_scan(session_id, target, platforms, categories, target_type):
    """Execute the scan in a background thread"""
    # Use Flask application context to ensure database access works correctly
    with app.app_context():
        try:
            session = ScanSession.query.get(session_id)
            if not session:
                return
            
            selected_categories = json.loads(categories) if categories else []
            total_steps = 0
            
            # Calculate total steps for progress tracking
            if platforms in ['google', 'both']:
                google_dorker = GoogleDorker()
                google_dorks = google_dorker.dork_manager.get_dorks('google', selected_categories)
                scan_progress[session_id]['google_dorks_total'] = len(google_dorks)
                total_steps += len(google_dorks)
            
            if platforms in ['github', 'both']:
                github_dorker = GithubDorker()
                github_dorks = github_dorker.dork_manager.get_dorks('github', selected_categories)
                scan_progress[session_id]['github_dorks_total'] = len(github_dorks)
                total_steps += len(github_dorks)
            
            scan_progress[session_id]['total_steps'] = total_steps
            
            # Run Google dorking if selected
            if platforms in ['google', 'both']:
                scan_progress[session_id]['status'] = 'running'
                scan_progress[session_id]['current_step'] = 'Executing Google dorks...'
                
                google_dorker = GoogleDorker(progress_callback=lambda dork, results: update_google_progress(session_id, dork))
                google_results = google_dorker.search(target, selected_categories)
                
                # Save results to database
                for result in google_results:
                    severity = 'medium'  # Default severity
                    
                    # Assign severity based on category
                    if result['category'].lower() in ['credentials', 'secrets', 'passwords', 'private keys']:
                        severity = 'high'
                    elif result['category'].lower() in ['sensitive files', 'backup files', 'config files']:
                        severity = 'medium'
                    elif result['category'].lower() in ['information disclosure', 'technology detection']:
                        severity = 'low'
                    
                    new_result = Result(
                        scan_session_id=session_id,
                        dork=result['dork'],
                        platform='google',
                        category=result['category'],
                        result_url=result['url'],
                        snippet=result['snippet'],
                        severity=severity
                    )
                    db.session.add(new_result)
                    db.session.commit()
                
            # Run GitHub dorking if selected
            if platforms in ['github', 'both']:
                scan_progress[session_id]['current_step'] = 'Executing GitHub dorks...'
                
                github_dorker = GithubDorker(progress_callback=lambda dork, results: update_github_progress(session_id, dork))
                github_results = github_dorker.search(target, selected_categories, target_type)
                
                # Save results to database
                for result in github_results:
                    severity = 'medium'  # Default severity
                    
                    # Assign severity based on category for GitHub findings
                    if result['category'].lower() in ['credentials', 'secrets', 'api keys', 'tokens']:
                        severity = 'high'
                    elif result['category'].lower() in ['configuration', 'database', 'env files']:
                        severity = 'medium'
                    elif result['category'].lower() in ['information', 'documentation']:
                        severity = 'low'
                        
                    # Keywords that might indicate high severity
                    high_severity_keywords = ['password', 'secret', 'key', 'token', 'credential', 'auth', 'ssh']
                    if any(keyword in result['dork'].lower() for keyword in high_severity_keywords):
                        severity = 'high'
                    
                    new_result = Result(
                        scan_session_id=session_id,
                        dork=result['dork'],
                        platform='github',
                        category=result['category'],
                        result_url=result['url'],
                        snippet=result['snippet'],
                        severity=severity
                    )
                    db.session.add(new_result)
                    db.session.commit()
            
            # Update session status to completed
            session = ScanSession.query.get(session_id)
            session.status = 'completed'
            session.completed_at = datetime.datetime.utcnow()
            db.session.commit()
            
            # Update progress
            scan_progress[session_id]['status'] = 'completed'
            scan_progress[session_id]['progress'] = 100
            scan_progress[session_id]['current_step'] = 'Scan completed successfully.'
            
        except Exception as e:
            # Handle errors
            print(f"Error in execute_scan: {str(e)}")
            try:
                session = ScanSession.query.get(session_id)
                if session:
                    session.status = 'failed'
                    session.error_message = str(e)
                    db.session.commit()
                
                # Update progress with error
                scan_progress[session_id]['status'] = 'failed'
                scan_progress[session_id]['current_step'] = f'Error: {str(e)}'
            except Exception as inner_e:
                print(f"Error handling exception in execute_scan: {str(inner_e)}")

def update_google_progress(session_id, dork):
    """Update progress for Google dorking"""
    if session_id in scan_progress:
        # These operations are just updating memory, not DB, so no app context needed
        scan_progress[session_id]['google_dorks_completed'] += 1
        scan_progress[session_id]['completed_steps'] += 1
        total = scan_progress[session_id]['total_steps']
        completed = scan_progress[session_id]['completed_steps']
        scan_progress[session_id]['progress'] = int((completed / total) * 100) if total > 0 else 0
        scan_progress[session_id]['current_step'] = f'Processing Google dork: {dork["template"][:40]}...'
        print(f"Progress update: {scan_progress[session_id]['progress']}% - {scan_progress[session_id]['current_step']}")

def update_github_progress(session_id, dork):
    """Update progress for GitHub dorking"""
    if session_id in scan_progress:
        # These operations are just updating memory, not DB, so no app context needed
        scan_progress[session_id]['github_dorks_completed'] += 1
        scan_progress[session_id]['completed_steps'] += 1
        total = scan_progress[session_id]['total_steps']
        completed = scan_progress[session_id]['completed_steps']
        scan_progress[session_id]['progress'] = int((completed / total) * 100) if total > 0 else 0
        scan_progress[session_id]['current_step'] = f'Processing GitHub dork: {dork["template"][:40]}...'
        print(f"Progress update: {scan_progress[session_id]['progress']}% - {scan_progress[session_id]['current_step']}")

@app.route('/api/scan/progress/<int:session_id>')
def get_scan_progress(session_id):
    """API endpoint to get scan progress"""
    if session_id not in scan_progress:
        # Check database for status if not in memory
        session = ScanSession.query.get_or_404(session_id)
        return jsonify({
            "session_id": session_id,
            "status": session.status,
            "progress": 100 if session.status == 'completed' else 0,
            "current_step": "Scan completed" if session.status == 'completed' else "Scan not in progress"
        })
    
    return jsonify({
        "session_id": session_id,
        "status": scan_progress[session_id]['status'],
        "progress": scan_progress[session_id]['progress'],
        "current_step": scan_progress[session_id]['current_step'],
        "details": {
            "google_dorks": {
                "total": scan_progress[session_id]['google_dorks_total'],
                "completed": scan_progress[session_id]['google_dorks_completed']
            },
            "github_dorks": {
                "total": scan_progress[session_id]['github_dorks_total'],
                "completed": scan_progress[session_id]['github_dorks_completed']
            }
        }
    })

@app.route('/api/session/<int:session_id>')
def get_session(session_id):
    """API endpoint to get session details"""
    session = ScanSession.query.get_or_404(session_id)
    results = Result.query.filter_by(scan_session_id=session_id).all()
    
    session_data = {
        "id": session.id,
        "target": session.target,
        "target_type": session.target_type,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "platforms": session.platforms,
        "categories": json.loads(session.categories) if session.categories else [],
        "error_message": session.error_message,
        "results_count": len(results)
    }
    
    results_data = [{
        "id": result.id,
        "dork": result.dork,
        "platform": result.platform,
        "category": result.category,
        "result_url": result.result_url,
        "snippet": result.snippet,
        "severity": result.severity,
        "is_false_positive": result.is_false_positive,
        "notes": result.notes,
        "timestamp": result.timestamp.isoformat()
    } for result in results]
    
    return jsonify({"session": session_data, "results": results_data})

@app.route('/api/sessions')
def get_sessions():
    """API endpoint to get all sessions"""
    sessions = ScanSession.query.order_by(ScanSession.created_at.desc()).all()
    sessions_data = [{
        "id": session.id,
        "target": session.target,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "platforms": session.platforms,
        "results_count": len(session.results)
    } for session in sessions]
    
    return jsonify({"sessions": sessions_data})

@app.route('/api/export/session/<int:session_id>/<format>')
def export_session(session_id, format):
    """API endpoint to export session results"""
    session = ScanSession.query.get_or_404(session_id)
    results = Result.query.filter_by(scan_session_id=session_id).all()
    
    if format == 'json':
        data = {
            "session": {
                "id": session.id,
                "target": session.target,
                "target_type": session.target_type,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "platforms": session.platforms,
                "categories": json.loads(session.categories) if session.categories else []
            },
            "results": [{
                "dork": result.dork,
                "platform": result.platform,
                "category": result.category,
                "result_url": result.result_url,
                "snippet": result.snippet,
                "severity": result.severity,
                "is_false_positive": result.is_false_positive,
                "notes": result.notes,
                "timestamp": result.timestamp.isoformat()
            } for result in results]
        }
        return jsonify(data)
    
    elif format == 'csv':
        # In a real app, this would generate and return a CSV file
        # For this example, we'll return a simplified CSV structure as text
        csv_content = "dork,platform,category,result_url,snippet,severity,is_false_positive,notes,timestamp\n"
        for result in results:
            # Escape commas and quotes in fields
            safe_snippet = result.snippet.replace('"', '""') if result.snippet else ""
            safe_notes = result.notes.replace('"', '""') if result.notes else ""
            csv_content += f'"{result.dork}",{result.platform},{result.category},"{result.result_url}","{safe_snippet}",{result.severity},{result.is_false_positive},"{safe_notes}",{result.timestamp.isoformat()}\n'
        
        return csv_content, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename=dorkrecon_export_{session_id}.csv'
        }
    
    return jsonify({"error": "Unsupported export format"}), 400

@app.route('/api/categories')
def get_categories():
    """API endpoint to get available dork categories"""
    platform = request.args.get('platform', 'both')
    
    categories = dork_manager.get_categories(platform)
    return jsonify({"categories": categories})

@app.route('/api/proxies', methods=['GET', 'POST', 'DELETE'])
def manage_proxies():
    """API endpoint to manage proxy servers"""
    if request.method == 'GET':
        proxies = ProxyServer.query.all()
        return jsonify({
            "proxies": [{
                "id": proxy.id,
                "address": proxy.address,
                "port": proxy.port,
                "protocol": proxy.protocol,
                "username": proxy.username,
                "is_active": proxy.is_active,
                "failure_count": proxy.failure_count
            } for proxy in proxies]
        })
    
    elif request.method == 'POST':
        data = request.json
        new_proxy = ProxyServer(
            address=data.get('address'),
            port=data.get('port'),
            protocol=data.get('protocol', 'http'),
            username=data.get('username'),
            password=data.get('password'),
            is_active=True
        )
        db.session.add(new_proxy)
        db.session.commit()
        return jsonify({"message": "Proxy added successfully", "id": new_proxy.id})
    
    elif request.method == 'DELETE':
        proxy_id = request.json.get('id')
        proxy = ProxyServer.query.get_or_404(proxy_id)
        db.session.delete(proxy)
        db.session.commit()
        return jsonify({"message": "Proxy deleted successfully"})
    
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/api/tokens', methods=['GET', 'POST', 'DELETE'])
def manage_tokens():
    """API endpoint to manage GitHub tokens"""
    if request.method == 'GET':
        tokens = GithubToken.query.all()
        return jsonify({
            "tokens": [{
                "id": token.id,
                "owner": token.owner,
                "rate_limit_remaining": token.rate_limit_remaining,
                "rate_limit_reset": token.rate_limit_reset.isoformat() if token.rate_limit_reset else None,
                "is_active": token.is_active
            } for token in tokens]
        })
    
    elif request.method == 'POST':
        data = request.json
        new_token = GithubToken(
            token=data.get('token'),
            owner=data.get('owner', 'Unknown'),
            is_active=True
        )
        db.session.add(new_token)
        db.session.commit()
        return jsonify({"message": "Token added successfully", "id": new_token.id})
    
    elif request.method == 'DELETE':
        token_id = request.json.get('id')
        token = GithubToken.query.get_or_404(token_id)
        db.session.delete(token)
        db.session.commit()
        return jsonify({"message": "Token deleted successfully"})
    
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/api/dorks')
def get_dorks():
    """API endpoint to get available dorks"""
    platform = request.args.get('platform', 'both')
    category = request.args.get('category')
    
    dorks = dork_manager.get_dorks(platform, category)
    return jsonify({"dorks": dorks})

@app.route('/api/result/<int:result_id>/severity', methods=['PUT'])
def update_result_severity(result_id):
    """API endpoint to update a result's severity level"""
    result = Result.query.get_or_404(result_id)
    data = request.json
    
    severity = data.get('severity')
    if severity not in ['high', 'medium', 'low']:
        return jsonify({"error": "Invalid severity level. Must be 'high', 'medium', or 'low'"}), 400
    
    result.severity = severity
    db.session.commit()
    
    return jsonify({
        "message": "Severity updated successfully",
        "result_id": result.id,
        "severity": result.severity
    })

@app.route('/api/result/<int:result_id>/false_positive', methods=['PUT'])
def mark_false_positive(result_id):
    """API endpoint to mark a result as a false positive"""
    result = Result.query.get_or_404(result_id)
    data = request.json
    
    is_false_positive = data.get('is_false_positive', True)
    notes = data.get('notes', '')
    
    result.is_false_positive = is_false_positive
    result.notes = notes
    db.session.commit()
    
    return jsonify({
        "message": "False positive status updated successfully",
        "result_id": result.id,
        "is_false_positive": result.is_false_positive,
        "notes": result.notes
    })

@app.route('/api/v1/scan/<int:session_id>/results')
def api_get_results(session_id):
    """API v1 endpoint to get results for a scan session"""
    session = ScanSession.query.get_or_404(session_id)
    results = Result.query.filter_by(scan_session_id=session_id).all()
    
    # Convert results to dictionaries
    result_dicts = [result.to_dict() for result in results]
    
    return jsonify({
        "scan_id": session_id,
        "target": session.target,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "platforms": session.platforms,
        "status": session.status,
        "result_count": len(result_dicts),
        "results": result_dicts
    })

@app.route('/api/v1/scans')
def api_get_scans():
    """API v1 endpoint to get all scan sessions"""
    sessions = ScanSession.query.order_by(ScanSession.created_at.desc()).all()
    
    session_data = []
    for session in sessions:
        result_count = Result.query.filter_by(scan_session_id=session.id).count()
        
        # Count results by severity
        high_count = Result.query.filter_by(scan_session_id=session.id, severity='high').count()
        medium_count = Result.query.filter_by(scan_session_id=session.id, severity='medium').count()
        low_count = Result.query.filter_by(scan_session_id=session.id, severity='low').count()
        false_positive_count = Result.query.filter_by(scan_session_id=session.id, is_false_positive=True).count()
        
        session_data.append({
            "id": session.id,
            "target": session.target,
            "target_type": session.target_type,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "platforms": session.platforms,
            "result_count": result_count,
            "severity_counts": {
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
                "false_positive": false_positive_count
            }
        })
    
    return jsonify({"scans": session_data})
