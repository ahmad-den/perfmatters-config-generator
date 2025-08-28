from flask import Flask, request, jsonify, render_template, send_file, abort
import json
import os
import logging
from datetime import datetime
import requests
from ad_detector import AdProviderDetector
from usage_logger import UsageLogger
import glob

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
usage_logger = UsageLogger()

# Global variables for configuration
optimization_dictionary = {}
default_template = {}

def load_configuration():
    """Load optimization dictionary and default template"""
    global optimization_dictionary, default_template
    
    try:
        # Load optimization dictionary
        with open('config/optimization_dictionary.json', 'r') as f:
            optimization_dictionary = json.load(f)
        logger.info("Optimization dictionary loaded successfully")
        
        # Load default template
        with open('templates/default_template.json', 'r') as f:
            default_template = json.load(f)
        logger.info("Default template loaded successfully")
        
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        # Initialize with empty configuration
        optimization_dictionary = {"plugins": {}, "themes": {}}
        default_template = {"perfmatters_options": {}, "perfmatters_tools": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        optimization_dictionary = {"plugins": {}, "themes": {}}
        default_template = {"perfmatters_options": {}, "perfmatters_tools": {}}

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
        # Create directory if it doesn't exist
        os.makedirs('generated_configs', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # microseconds to milliseconds
        filename = f"perfmatters_config_{timestamp}.json"
        filepath = os.path.join('generated_configs', filename)
        
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
        config_files = glob.glob('generated_configs/perfmatters_config_*.json')
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

@app.route('/')
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
        
        filepath = os.path.join('generated_configs', filename)
        
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
    usage_logger.log_health_check(get_client_ip())
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/generate-config', methods=['POST'])
def generate_config():
    """Generate Perfmatters configuration based on plugins and theme"""
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
        
        # Create a copy of the default template
        config = json.loads(json.dumps(default_template))
        
        # Initialize exclusion lists
        js_exclusions = []
        delay_js_exclusions = []
        rucss_excluded_stylesheets = []
        rucss_excluded_selectors = []
        minify_css_exclusions = []
        minify_js_exclusions = []
        
        # Add universal exclusions
        universal = optimization_dictionary.get('universal', {})
        js_exclusions.extend(universal.get('js_exclusions', []))
        delay_js_exclusions.extend(universal.get('delay_js_exclusions', []))
        rucss_excluded_stylesheets.extend(universal.get('rucss_excluded_stylesheets', []))
        rucss_excluded_selectors.extend(universal.get('rucss_excluded_selectors', []))
        minify_css_exclusions.extend(universal.get('minify_css_exclusions', []))
        minify_js_exclusions.extend(universal.get('minify_js_exclusions', []))
        
        # Process plugins
        plugins_processed = 0
        plugin_configs = optimization_dictionary.get('plugins', {})
        
        for plugin in plugins:
            if plugin in plugin_configs:
                plugin_config = plugin_configs[plugin]
                js_exclusions.extend(plugin_config.get('js_exclusions', []))
                delay_js_exclusions.extend(plugin_config.get('delay_js_exclusions', []))
                rucss_excluded_stylesheets.extend(plugin_config.get('rucss_excluded_stylesheets', []))
                rucss_excluded_selectors.extend(plugin_config.get('rucss_excluded_selectors', []))
                minify_css_exclusions.extend(plugin_config.get('minify_css_exclusions', []))
                minify_js_exclusions.extend(plugin_config.get('minify_js_exclusions', []))
                plugins_processed += 1
        
        # Process themes (support multiple themes)
        themes_processed = 0
        theme_configs = optimization_dictionary.get('themes', {})
        
        for theme_name in themes:
            if theme_name in theme_configs:
                theme_config = theme_configs[theme_name]
                js_exclusions.extend(theme_config.get('js_exclusions', []))
                delay_js_exclusions.extend(theme_config.get('delay_js_exclusions', []))
                rucss_excluded_stylesheets.extend(theme_config.get('rucss_excluded_stylesheets', []))
                rucss_excluded_selectors.extend(theme_config.get('rucss_excluded_selectors', []))
                minify_css_exclusions.extend(theme_config.get('minify_css_exclusions', []))
                minify_js_exclusions.extend(theme_config.get('minify_js_exclusions', []))
                themes_processed += 1
        
        # Domain analysis for ad providers
        detected_ad_providers = []
        if analyze_domain and domain:
            try:
                ad_detector = AdProviderDetector()
                ad_exclusions = ad_detector.get_ad_exclusions(domain, timeout=10)
                
                # Add ad provider exclusions
                js_exclusions.extend(ad_exclusions.get('js_exclusions', []))
                delay_js_exclusions.extend(ad_exclusions.get('delay_js_exclusions', []))
                rucss_excluded_stylesheets.extend(ad_exclusions.get('rucss_exclusions', []))
                rucss_excluded_selectors.extend(ad_exclusions.get('rucss_excluded_selectors', []))
                minify_css_exclusions.extend(ad_exclusions.get('minify_css_exclusions', []))
                minify_js_exclusions.extend(ad_exclusions.get('minify_js_exclusions', []))
                
                # Track detected providers (this would need to be implemented in ad_detector)
                # For now, we'll leave this empty
                detected_ad_providers = []
                
            except Exception as e:
                logger.error(f"Domain analysis failed for {domain}: {e}")
        
        # Remove duplicates and convert to newline-separated strings
        js_exclusions = '\n'.join(list(dict.fromkeys(js_exclusions)))
        delay_js_exclusions = '\n'.join(list(dict.fromkeys(delay_js_exclusions)))
        rucss_excluded_stylesheets = '\n'.join(list(dict.fromkeys(rucss_excluded_stylesheets)))
        rucss_excluded_selectors = '\n'.join(list(dict.fromkeys(rucss_excluded_selectors)))
        minify_css_exclusions = '\n'.join(list(dict.fromkeys(minify_css_exclusions)))
        minify_js_exclusions = '\n'.join(list(dict.fromkeys(minify_js_exclusions)))
        
        # Update configuration
        if 'perfmatters_options' not in config:
            config['perfmatters_options'] = {}
        if 'assets' not in config['perfmatters_options']:
            config['perfmatters_options']['assets'] = {}
        
        config['perfmatters_options']['assets']['js_exclusions'] = js_exclusions
        config['perfmatters_options']['assets']['delay_js_exclusions'] = delay_js_exclusions
        config['perfmatters_options']['assets']['rucss_excluded_stylesheets'] = rucss_excluded_stylesheets
        config['perfmatters_options']['assets']['rucss_excluded_selectors'] = rucss_excluded_selectors
        config['perfmatters_options']['assets']['minify_css_exclusions'] = minify_css_exclusions
        config['perfmatters_options']['assets']['minify_js_exclusions'] = minify_js_exclusions
        
        # Prepare response
        processing_info = {
            'plugins_processed': plugins_processed,
            'themes_processed': themes_processed,
            'theme_processed': themes_processed > 0  # Legacy field for backward compatibility
        }
        
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
    """Reload configuration files"""
    client_ip = get_client_ip()
    
    try:
        load_configuration()
        usage_logger.log_config_reload(client_ip, success=True)
        
        return jsonify({
            'success': True,
            'message': 'Configuration files reloaded successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        usage_logger.log_config_reload(client_ip, success=False, error_message=str(e))
        
        return jsonify({
            'success': False,
            'error': 'Failed to reload configuration'
        }), 500

# Initialize configuration on startup
load_configuration()

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('generated_configs', exist_ok=True)
    
    # Run the application
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 8080)),
        debug=os.getenv('DEBUG', 'False').lower() == 'true'
    )