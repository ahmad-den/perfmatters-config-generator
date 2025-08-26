import os
import json
import logging
import re
import copy
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, Response
from flask import Flask, request, jsonify, Response, send_file
from typing import Dict, List, Optional, Tuple, Any
import tempfile
from ad_detector import AdProviderDetector
from ad_detector import AdProviderDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class PerfmattersConfigGenerator:
    """Main class for generating Perfmatters configurations"""
    
    def __init__(self):
        self.template_string = ""
        self.rucss_dict = {}
        self.delayjs_dict = {}
        self.js_dict = {}
        self.ad_detector = AdProviderDetector()
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
        
        # Update the config with collected exclusions
        
        # Parse template and update directly
        try:
            final_config = json.loads(self.template_string)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template JSON at position {e.pos}: {e.msg}")
            logger.error(f"Template content around error: {self.template_string[max(0, e.pos-50):e.pos+50]}")
            logger.error(f"Full template content: {self.template_string}")
            raise
        
        # Update the assets section with collected exclusions
        assets = final_config['perfmatters_options']['assets']
        assets['js_exclusions'] = js_exclusions
        assets['delay_js_exclusions'] = delay_js_exclusions
        assets['rucss_excluded_stylesheets'] = rucss_excluded_stylesheets
        assets['rucss_excluded_selectors'] = rucss_excluded_selectors
        assets['minify_css_exclusions'] = minify_css_exclusions
        assets['minify_js_exclusions'] = minify_js_exclusions
        
        # Special handling for Kadence themes - disable remove_comment_urls
        if self._is_kadence_theme(themes_to_process):
            final_config['perfmatters_options']['remove_comment_urls'] = ""
            logger.info("Kadence theme detected - disabled remove_comment_urls")
        
        # Return the complete configuration
        return final_config
        
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/generate-config', methods=['POST'])
def generate_config():
    """Main endpoint to generate Perfmatters configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON data'
            }), 400
        
        # Extract required parameters
        plugins = data.get('plugins', [])
        theme = data.get('theme', '')
        themes = data.get('themes', [])
        theme_parent = data.get('theme_parent', '')
        theme_child = data.get('theme_child', '')
        domain = data.get('domain', '')
        analyze_domain = data.get('analyze_domain', False)
        
        if not isinstance(plugins, list):
            return jsonify({
                'success': False,
                'error': 'Plugins must be provided as a list'
            }), 400
        
        # Generate configuration
        config_result = config_generator.generate_config(
            plugins=plugins,
            theme=theme,
            themes=themes,
            theme_parent=theme_parent,
            theme_child=theme_child,
            domain=domain,
            analyze_domain=analyze_domain
        )
        
        # Prepare response
        # Create a temporary file with the JSON config
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(config_result, temp_file, separators=(',', ':'), ensure_ascii=False, indent=2)
        temp_file.close()
        
        # Generate filename based on plugins and theme
        plugins_str = '-'.join(plugins[:3]) if plugins else 'no-plugins'  # Limit to first 3 plugins
        theme_str = theme if theme else 'no-theme'
        filename = f"perfmatters-config-{plugins_str}-{theme_str}.json"
        
        # Return the file as download
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error generating config: {e}")
        return Response(json.dumps({
            'success': False,
            'error': str(e)
        }, separators=(',', ':')), status=500, mimetype='application/json')

@app.route('/reload-config', methods=['POST'])
def reload_config():
    """Reload configuration files without restarting server"""
    try:
        config_generator.load_configurations()
        return jsonify({
            'success': True,
            'message': 'Configuration files reloaded successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/detect-ads', methods=['POST'])
def detect_ads():
    """Endpoint to detect ad providers from a URL"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON data'
            }), 400
        
        url = data.get('url', '')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        # Detect ad providers
        result = config_generator.ad_detector.detect_ad_providers(url)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error detecting ads: {e}")
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
    
    # Run the application
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)