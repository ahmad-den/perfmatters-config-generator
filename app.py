from flask import Flask, request, jsonify, render_template, send_file, abort
import json
import os
import logging
from datetime import datetime
import requests
from ad_detector import AdProviderDetector
from usage_logger import UsageLogger
import glob
import re
import copy
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple, Any
import tempfile
from dotenv import load_dotenv
from functools import wraps
from flask import session
from flask import redirect, url_for
import bcrypt
import secrets

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
usage_logger = UsageLogger()

class PerfmattersConfigGenerator:
    """Main class for generating Perfmatters configurations"""

    def __init__(self):
        self.template_string = ""
        self.rucss_dict = {}
        self.delayjs_dict = {}
        self.js_dict = {}
        self.ad_detector = AdProviderDetector()
        self.load_configurations()

    def load_configurations(self):
        """Load default template and optimization dictionaries from files"""
        try:
            # Load default template
            template_path = os.path.join('templates', 'default_template.json')
            with open(template_path, 'r', encoding='utf-8') as f:
                self.template_string = f.read().strip()
            logger.info("Default template loaded successfully")

            # Load RUCSS dictionary
            rucss_path = os.path.join('config', 'dictionary_rucss.json')
            with open(rucss_path, 'r', encoding='utf-8') as f:
                self.rucss_dict = json.load(f)
            logger.info("RUCSS dictionary loaded successfully")

            # Load Delay JS dictionary
            delayjs_path = os.path.join('config', 'dictionary_delayjs.json')
            with open(delayjs_path, 'r', encoding='utf-8') as f:
                self.delayjs_dict = json.load(f)
            logger.info("Delay JS dictionary loaded successfully")

            # Load JS dictionary
            js_path = os.path.join('config', 'dictionary_js.json')
            with open(js_path, 'r', encoding='utf-8') as f:
                self.js_dict = json.load(f)
            logger.info("JS dictionary loaded successfully")

        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise

    def generate_config(self, plugins: List[str], theme: str, domain: Optional[str] = None,
                       analyze_domain: bool = False, themes: Optional[List[str]] = None,
                       theme_parent: Optional[str] = None, theme_child: Optional[str] = None) -> Dict[str, Any]:
        """Generate Perfmatters configuration based on plugins, theme, and optional domain analysis"""

        processing_info = {
            'plugins_processed': 0,
            'themes_processed': 0
        }

        # Collect all exclusions
        js_exclusions = []
        delay_js_exclusions = []
        rucss_excluded_stylesheets = []
        rucss_excluded_selectors = []
        minify_css_exclusions = []
        minify_js_exclusions = []

        # Apply universal exclusions from RUCSS dictionary
        rucss_universal = self.rucss_dict.get('universal', {})
        rucss_excluded_stylesheets.extend(rucss_universal.get('rucss_excluded_stylesheets', []))

        # Apply universal exclusions from Delay JS dictionary
        delayjs_universal = self.delayjs_dict.get('universal', {})
        delay_js_exclusions.extend(delayjs_universal.get('delay_js_exclusions', []))

        # Apply universal exclusions from JS dictionary
        js_universal = self.js_dict.get('universal', {})
        js_exclusions.extend(js_universal.get('js_exclusions', []))

        # Analyze domain for ad providers if requested
        detected_ad_providers = []
        if analyze_domain and domain:
            logger.info(f"Analyzing domain for ad providers: {domain}")
            ad_exclusions = self.ad_detector.get_ad_exclusions(domain)
            if any(ad_exclusions.values()):
                logger.info("Applied ad provider exclusions based on detection")
                js_exclusions.extend(ad_exclusions['js_exclusions'])
                rucss_excluded_stylesheets.extend(ad_exclusions['rucss_exclusions'])
                delay_js_exclusions.extend(ad_exclusions['delay_js_exclusions'])
                rucss_excluded_selectors.extend(ad_exclusions['rucss_excluded_selectors'])
                minify_css_exclusions.extend(ad_exclusions['minify_css_exclusions'])
                minify_js_exclusions.extend(ad_exclusions['minify_js_exclusions'])

        # Process plugins
        for plugin in plugins:
            # Get RUCSS exclusions for plugin
            rucss_plugin_settings = self._get_plugin_rucss_optimizations(plugin)
            if rucss_plugin_settings:
                rucss_excluded_stylesheets.extend(rucss_plugin_settings.get('rucss_excluded_stylesheets', []))
                processing_info['plugins_processed'] += 1

            # Get Delay JS exclusions for plugin
            delayjs_plugin_settings = self._get_plugin_delayjs_optimizations(plugin)
            if delayjs_plugin_settings:
                delay_js_exclusions.extend(delayjs_plugin_settings.get('delay_js_exclusions', []))

            # Get JS exclusions for plugin
            js_plugin_settings = self._get_plugin_js_optimizations(plugin)
            if js_plugin_settings:
                js_exclusions.extend(js_plugin_settings.get('js_exclusions', []))

        # Process themes (multiple theme support)
        themes_to_process = []

        if themes:
            # Use the themes array if provided
            themes_to_process = themes
        else:
            # Fallback to individual theme fields for backward compatibility
            if theme_parent:
                themes_to_process.append(theme_parent)
            if theme_child and theme_child != theme_parent:
                themes_to_process.append(theme_child)
            if not themes_to_process and theme:
                themes_to_process.append(theme)

        # Remove duplicates while preserving order
        seen = set()
        themes_to_process = [t for t in themes_to_process if not (t in seen or seen.add(t))]

        # Process each theme
        for theme_name in themes_to_process:
            # Get RUCSS exclusions for theme
            rucss_theme_settings = self._get_theme_rucss_optimizations(theme_name)
            if rucss_theme_settings:
                rucss_excluded_stylesheets.extend(rucss_theme_settings.get('rucss_excluded_stylesheets', []))
                processing_info['themes_processed'] += 1

            # Get Delay JS exclusions for theme
            delayjs_theme_settings = self._get_theme_delayjs_optimizations(theme_name)
            if delayjs_theme_settings:
                delay_js_exclusions.extend(delayjs_theme_settings.get('delay_js_exclusions', []))

            # Get JS exclusions for theme
            js_theme_settings = self._get_theme_js_optimizations(theme_name)
            if js_theme_settings:
                js_exclusions.extend(js_theme_settings.get('js_exclusions', []))

        # Parse template and update directly
        try:
            final_config = json.loads(self.template_string)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template JSON at position {e.pos}: {e.msg}")
            raise

        # Update the assets section with collected exclusions
        assets = final_config['perfmatters_options']['assets']
        assets['js_exclusions'] = '\n'.join(list(dict.fromkeys(js_exclusions)))
        assets['delay_js_exclusions'] = '\n'.join(list(dict.fromkeys(delay_js_exclusions)))
        assets['rucss_excluded_stylesheets'] = '\n'.join(list(dict.fromkeys(rucss_excluded_stylesheets)))
        assets['rucss_excluded_selectors'] = '\n'.join(list(dict.fromkeys(rucss_excluded_selectors)))
        assets['minify_css_exclusions'] = '\n'.join(list(dict.fromkeys(minify_css_exclusions)))
        assets['minify_js_exclusions'] = '\n'.join(list(dict.fromkeys(minify_js_exclusions)))

        # Special handling for Kadence themes - disable remove_comment_urls
        if self._is_kadence_theme(themes_to_process):
            final_config['perfmatters_options']['remove_comment_urls'] = ""
            logger.info("Kadence theme detected - disabled remove_comment_urls")

        # Return the complete configuration with processing info
        return {
            'config': final_config,
            'processing_info': processing_info,
            'detected_ad_providers': detected_ad_providers
        }

    def _get_plugin_rucss_optimizations(self, plugin: str) -> Optional[Dict[str, Any]]:
        """Get RUCSS optimizations for a specific plugin"""
        plugins_config = self.rucss_dict.get('plugins', {})
        plugin_key = self._normalize_plugin_name(plugin)

        if plugin_key in plugins_config:
            logger.info(f"Applied RUCSS optimizations for plugin: {plugin}")
            return plugins_config[plugin_key]

        return None

    def _get_plugin_delayjs_optimizations(self, plugin: str) -> Optional[Dict[str, Any]]:
        """Get Delay JS optimizations for a specific plugin"""
        plugins_config = self.delayjs_dict.get('plugins', {})
        plugin_key = self._normalize_plugin_name(plugin)

        if plugin_key in plugins_config:
            logger.info(f"Applied Delay JS optimizations for plugin: {plugin}")
            return plugins_config[plugin_key]

        return None

    def _get_plugin_js_optimizations(self, plugin: str) -> Optional[Dict[str, Any]]:
        """Get JS optimizations for a specific plugin"""
        plugins_config = self.js_dict.get('plugins', {})
        plugin_key = self._normalize_plugin_name(plugin)

        if plugin_key in plugins_config:
            logger.info(f"Applied JS optimizations for plugin: {plugin}")
            return plugins_config[plugin_key]

        return None

    def _get_theme_rucss_optimizations(self, theme: str) -> Optional[Dict[str, Any]]:
        """Get RUCSS optimizations for a specific theme"""
        themes_config = self.rucss_dict.get('themes', {})
        theme_key = self._normalize_theme_name(theme)

        if theme_key in themes_config:
            logger.info(f"Applied RUCSS optimizations for theme: {theme}")
            return themes_config[theme_key]

        return None

    def _get_theme_delayjs_optimizations(self, theme: str) -> Optional[Dict[str, Any]]:
        """Get Delay JS optimizations for a specific theme"""
        themes_config = self.delayjs_dict.get('themes', {})
        theme_key = self._normalize_theme_name(theme)

        if theme_key in themes_config:
            logger.info(f"Applied Delay JS optimizations for theme: {theme}")
            return themes_config[theme_key]

        return None

    def _get_theme_js_optimizations(self, theme: str) -> Optional[Dict[str, Any]]:
        """Get JS optimizations for a specific theme"""
        themes_config = self.js_dict.get('themes', {})
        theme_key = self._normalize_theme_name(theme)

        if theme_key in themes_config:
            logger.info(f"Applied JS optimizations for theme: {theme}")
            return themes_config[theme_key]

        return None

    def _normalize_plugin_name(self, plugin: str) -> str:
        """Normalize plugin name for dictionary lookup"""
        # Remove version numbers and common suffixes
        plugin = re.sub(r'/.*$', '', plugin)  # Remove path after plugin name
        plugin = re.sub(r'\s+\d+.*$', '', plugin)  # Remove version numbers
        return plugin.lower().replace(' ', '-').replace('_', '-')

    def _normalize_theme_name(self, theme: str) -> str:
        """Normalize theme name for dictionary lookup"""
        return theme.lower().replace(' ', '-').replace('_', '-')

    def _is_kadence_theme(self, themes: List[str]) -> bool:
        """Check if any of the themes is Kadence-based"""
        for theme in themes:
            if 'kadence' in theme.lower():
                return True
        return False

# Global instance
config_generator = PerfmattersConfigGenerator()

def is_authenticated():
    """Check if user is authenticated via session"""
    return session.get('authenticated', False) and session.get('auth_token') == get_auth_token()

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_auth_token():
    """Generate a secure auth token based on session and server secret"""
    session_id = session.get('session_id', '')
    server_secret = app.secret_key
    return bcrypt.hashpw((session_id + server_secret).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')[:32]

def verify_password(password):
    """Verify password securely"""
    stored_password = os.getenv('DASHBOARD_PASSWORD', 'admin123')
    
    # If stored password is already hashed (starts with $2b$), verify against hash
    if stored_password.startswith('$2b$'):
        return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
    else:
        # For backward compatibility, compare plain text but recommend hashing
        logger.warning("Dashboard password is stored in plain text. Consider hashing it.")
        return password == stored_password

def get_client_ip():
    """Get client IP address from request headers"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def save_generated_config(config_data, metadata):
    """Save generated configuration with metadata"""
    try:
        # Use /opt/perfmatters-api/generated_configs
        config_dir = '/opt/perfmatters-api/generated_configs'
        os.makedirs(config_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # microseconds to milliseconds
        filename = f"perfmatters_config_{timestamp}.json"
        filepath = os.path.join(config_dir, filename)
        
        # Prepare data to save (config + metadata)
        save_data = {
            'metadata': metadata,
            'config': config_data
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        logger.info(f"Configuration saved to {filepath}")
        return filename
        
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return None

def load_saved_configs():
    """Load all saved configurations with metadata"""
    configs = []
    
    try:
        config_dir = '/opt/perfmatters-api/generated_configs'
        config_files = glob.glob(os.path.join(config_dir, 'perfmatters_config_*.json'))
        config_files.sort(key=os.path.getmtime, reverse=True)  # Most recent first
        
        for filepath in config_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                # Extract metadata
                metadata = data.get('metadata', {})
                
                # Add file info
                filename = os.path.basename(filepath)
                file_size = os.path.getsize(filepath)
                
                config_info = {
                    'filename': filename,
                    'file_size': file_size,
                    'domain': metadata.get('domain', 'No domain'),
                    'client_ip': metadata.get('client_ip', 'Unknown'),
                    'generated_at': metadata.get('generated_at', 'Unknown'),
                    'plugins_count': metadata.get('plugins_count', 0),
                    'theme': metadata.get('theme', 'Unknown'),
                    'detected_ad_providers': metadata.get('detected_ad_providers', [])
                }
                
                configs.append(config_info)
                
            except Exception as e:
                logger.error(f"Failed to load config {filepath}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Failed to load saved configurations: {e}")
    
    return configs

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for dashboard access"""
    if is_authenticated():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if verify_password(password):
            # Generate secure session
            session_id = secrets.token_hex(16)
            session['session_id'] = session_id
            session['authenticated'] = True
            session['auth_token'] = get_auth_token()
            session.permanent = True  # Make session persistent
            return redirect(url_for('dashboard'))
        else:
            logger.warning(f"Failed login attempt from IP: {get_client_ip()}")
            return render_template('login.html', error='Invalid password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@require_auth
def dashboard():
    """Dashboard showing all generated configurations"""
    try:
        configs = load_saved_configs()
        return render_template('dashboard.html', configs=configs)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard'
        }), 500

@app.route('/download/<filename>')
def download_config(filename):
    """Download a specific configuration file"""
    try:
        # Validate filename to prevent directory traversal
        if not filename.startswith('perfmatters_config_') or not filename.endswith('.json'):
            abort(404)
        
        config_dir = '/opt/perfmatters-api/generated_configs'
        filepath = os.path.join(config_dir, filename)
        
        if not os.path.exists(filepath):
            abort(404)
        
        # Load the file and extract just the config (without metadata)
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config_only = data.get('config', data)  # Fallback to full data if no config key
        
        # Create a temporary file with just the config
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(config_only, temp_file, indent=2)
            temp_filepath = temp_file.name
        
        def remove_temp_file(response):
            try:
                os.unlink(temp_filepath)
            except:
                pass
            return response
        
        return send_file(
            temp_filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Download error for {filename}: {e}")
        abort(500)

@app.route('/api/configs')
@require_auth
def api_configs():
    """API endpoint to get all configurations as JSON"""
    try:
        configs = load_saved_configs()
        return jsonify({
            'success': True,
            'configs': configs,
            'total': len(configs)
        })
    except Exception as e:
        logger.error(f"API configs error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load configurations'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    usage_logger.log_health_check(user_ip=get_client_ip())
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/generate-config', methods=['POST'])
def generate_config():
    """Main endpoint to generate Perfmatters configuration"""
    client_ip = get_client_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')

    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'plugins' not in data:
            return jsonify({
                'success': False,
                'error': 'plugins field is required'
            }), 400
        
        plugins = data.get('plugins', [])
        theme = data.get('theme', 'default')
        themes = data.get('themes', [theme])  # Support multiple themes
        theme_parent = data.get('theme_parent', theme)
        theme_child = data.get('theme_child', theme)
        domain = data.get('domain', '')
        analyze_domain = data.get('analyze_domain', False)
        
        # Ensure plugins is a list
        if not isinstance(plugins, list):
            return jsonify({
                'success': False,
                'error': 'plugins must be an array'
            }), 400

        # Generate configuration using the config generator
        result = config_generator.generate_config(
            plugins=plugins,
            theme=theme,
            themes=themes,
            theme_parent=theme_parent,
            theme_child=theme_child,
            domain=domain,
            analyze_domain=analyze_domain
        )
        
        config = result['config']
        processing_info = result['processing_info']
        detected_ad_providers = result['detected_ad_providers']
        
        generated_at = datetime.now().isoformat()
        
        # Prepare metadata for saving
        metadata = {
            'domain': domain,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'generated_at': generated_at,
            'plugins': plugins,
            'plugins_count': len(plugins),
            'theme': theme,
            'themes': themes,
            'theme_parent': theme_parent,
            'theme_child': theme_child,
            'analyze_domain': analyze_domain,
            'detected_ad_providers': detected_ad_providers,
            'processing_info': processing_info
        }
        
        # Save configuration
        filename = save_generated_config(config, metadata)
        
        # Log usage
        usage_logger.log_config_generation(
            plugins=plugins,
            theme=theme,
            themes=themes,
            theme_parent=theme_parent,
            theme_child=theme_child,
            domain=domain,
            analyze_domain=analyze_domain,
            detected_ad_providers=detected_ad_providers,
            processing_info=processing_info,
            user_ip=client_ip,
            user_agent=user_agent,
            success=True
        )
        
        response_data = {
            'success': True,
            'config': config,
            'processing_info': processing_info,
            'generated_at': generated_at
        }
        
        if filename:
            response_data['saved_as'] = filename
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating configuration: {e}")
        
        # Log failed attempt
        usage_logger.log_config_generation(
            plugins=data.get('plugins', []) if 'data' in locals() else [],
            theme=data.get('theme', 'unknown') if 'data' in locals() else 'unknown',
            domain=data.get('domain', '') if 'data' in locals() else '',
            user_ip=client_ip,
            user_agent=user_agent,
            success=False,
            error_message=str(e)
        )
        
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/reload-config', methods=['POST'])
def reload_config():
    """Reload configuration files without restarting server"""
    client_ip = get_client_ip()
    try:
        config_generator.load_configurations()
        usage_logger.log_config_reload(user_ip=client_ip, success=True)
        return jsonify({
            'success': True,
            'message': 'Configuration files reloaded successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        usage_logger.log_config_reload(user_ip=client_ip, success=False, error_message=str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/detect-ads', methods=['POST'])
def detect_ads():
    """Endpoint to detect ad providers from a URL"""
    client_ip = get_client_ip()
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON data'
            }), 400

        url = data.get('url', '')

        if not url:
            usage_logger.log_ad_detection(
                domain='',
                detected_providers=[],
                user_ip=client_ip,
                success=False,
                error_message='URL is required'
            )
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400

        # Detect ad providers
        result = config_generator.ad_detector.get_ad_exclusions(url)

        # Log ad detection usage
        usage_logger.log_ad_detection(
            domain=url,
            detected_providers=[],  # Ad detector doesn't return provider names in current implementation
            user_ip=client_ip,
            success=True
        )

        return jsonify({
            'success': True,
            'exclusions': result
        })

    except Exception as e:
        logger.error(f"Error detecting ads: {e}")
        usage_logger.log_ad_detection(
            domain=url if 'url' in locals() else 'Unknown',
            detected_providers=[],
            user_ip=client_ip,
            success=False,
            error_message=str(e)
        )
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('generated_configs', exist_ok=True)

    # Run the application
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'

    app.run(host=host, port=port, debug=debug)