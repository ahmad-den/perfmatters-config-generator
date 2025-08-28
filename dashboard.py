import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash
import tempfile
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DashboardManager:
    """Handles the web dashboard functionality"""
    
    def __init__(self, config_generator, usage_logger):
        self.config_generator = config_generator
        self.usage_logger = usage_logger
        self.dashboard_password = os.getenv('DASHBOARD_PASSWORD', 'admin123')
        
    def setup_routes(self, app):
        """Setup dashboard routes"""
        
        @app.route('/')
        def dashboard_home():
            """Main dashboard page"""
            if not self._is_authenticated():
                return redirect(url_for('dashboard_login'))
            
            return render_template('dashboard.html')
        
        @app.route('/login', methods=['GET', 'POST'])
        def dashboard_login():
            """Dashboard login page"""
            if request.method == 'POST':
                password = request.form.get('password', '')
                
                if self._verify_password(password):
                    session['authenticated'] = True
                    session['login_time'] = datetime.now().isoformat()
                    logger.info(f"Dashboard login successful from IP: {self._get_client_ip()}")
                    return redirect(url_for('dashboard_home'))
                else:
                    logger.warning(f"Dashboard login failed from IP: {self._get_client_ip()}")
                    return render_template('login.html', error='Invalid password')
            
            return render_template('login.html')
        
        @app.route('/logout')
        def dashboard_logout():
            """Dashboard logout"""
            session.clear()
            return redirect(url_for('dashboard_login'))
        
        @app.route('/api/generate-dashboard-config', methods=['POST'])
        def generate_dashboard_config():
            """Generate config from dashboard"""
            if not self._is_authenticated():
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401
            
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400
                
                plugins = data.get('plugins', [])
                theme = data.get('theme', '')
                domain = data.get('domain', '')
                analyze_domain = data.get('analyze_domain', False)
                
                # Generate configuration using existing generator
                config_result = self.config_generator.generate_config(
                    plugins=plugins,
                    theme=theme,
                    domain=domain,
                    analyze_domain=analyze_domain
                )
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(config_result, temp_file, separators=(',', ':'), ensure_ascii=False, indent=2)
                temp_file.close()
                
                # Log the generation
                user_ip = self._get_client_ip()
                self.usage_logger.log_config_generation(
                    plugins=plugins,
                    theme=theme,
                    domain=domain,
                    analyze_domain=analyze_domain,
                    user_ip=user_ip,
                    user_agent=request.headers.get('User-Agent', 'Dashboard'),
                    success=True
                )
                
                return jsonify({
                    'success': True,
                    'download_url': f'/download-config/{os.path.basename(temp_file.name)}',
                    'config_preview': {
                        'plugins_count': len(plugins),
                        'theme': theme,
                        'domain': domain,
                        'generated_at': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                logger.error(f"Dashboard config generation error: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/download-config/<filename>')
        def download_config(filename):
            """Download generated config file"""
            if not self._is_authenticated():
                return jsonify({'error': 'Not authenticated'}), 401
            
            try:
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                if os.path.exists(temp_path):
                    return send_file(
                        temp_path,
                        as_attachment=True,
                        download_name=f"perfmatters-config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
                        mimetype='application/json'
                    )
                else:
                    return jsonify({'error': 'File not found'}), 404
            except Exception as e:
                logger.error(f"Download error: {e}")
                return jsonify({'error': 'Download failed'}), 500
    
    def _is_authenticated(self):
        """Check if user is authenticated"""
        return session.get('authenticated', False)
    
    def _verify_password(self, password):
        """Verify dashboard password"""
        try:
            # Check if password is hashed (starts with $2b$)
            if self.dashboard_password.startswith('$2b$'):
                return check_password_hash(self.dashboard_password, password)
            else:
                # Plain text comparison (with warning)
                logger.warning("Dashboard password is stored in plain text. Consider hashing it.")
                return password == self.dashboard_password
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _get_client_ip(self):
        """Get client IP address"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        else:
            return request.remote_addr