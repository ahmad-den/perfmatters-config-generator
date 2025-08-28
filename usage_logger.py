import os
import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

class UsageLogger:
    """Logs API usage and sends notifications to Slack"""
    
    def __init__(self):
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.slack_channel = os.getenv('SLACK_CHANNEL', '#perfmatters-checkmysite')
        
        # Initialize SQLite database for usage stats
        self.db_path = '/opt/perfmatters-api/logs/usage_stats.db'
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Initialize Slack client if webhook URL is provided
        self.slack_client = None
        if self.slack_webhook_url:
            try:
                # Extract token from webhook URL for WebClient
                # For webhook URLs, we'll use requests instead
                import requests
                self.requests = requests
                logger.info("Slack webhook configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Slack: {e}")
    
    def _init_database(self):
        """Initialize SQLite database for usage statistics"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS usage_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        domain TEXT,
                        user_ip TEXT,
                        user_agent TEXT,
                        plugins_count INTEGER DEFAULT 0,
                        theme TEXT,
                        success BOOLEAN NOT NULL,
                        config_json TEXT,
                        error_message TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster queries
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_stats(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_endpoint ON usage_stats(endpoint)')
                
            logger.info("Usage statistics database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize usage database: {e}")
    
    def _save_to_database(self, usage_data: Dict[str, Any], config_json: Optional[str] = None):
        """Save usage data to SQLite database"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT INTO usage_stats 
                        (timestamp, endpoint, domain, user_ip, user_agent, plugins_count, theme, success, config_json, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        usage_data.get('timestamp'),
                        usage_data.get('endpoint'),
                        usage_data.get('domain'),
                        usage_data.get('user_ip'),
                        usage_data.get('user_agent'),
                        usage_data.get('plugin_count', 0),
                        usage_data.get('theme'),
                        usage_data.get('success', False),
                        config_json,
                        usage_data.get('error_message')
                    ))
        except Exception as e:
            logger.error(f"Failed to save usage data to database: {e}")
    
    def get_recent_usage(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent usage statistics from database"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute('''
                        SELECT * FROM usage_stats 
                        WHERE endpoint = 'generate-config'
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch usage statistics: {e}")
            return []
    
    def log_config_generation(self, 
                            plugins: List[str], 
                            theme: str,
                            themes: Optional[List[str]] = None,
                            theme_parent: Optional[str] = None,
                            theme_child: Optional[str] = None,
                            domain: Optional[str] = None,
                            analyze_domain: bool = False,
                            detected_ad_providers: Optional[List[str]] = None,
                            processing_info: Optional[Dict] = None,
                            user_ip: Optional[str] = None,
                            user_agent: Optional[str] = None,
                            success: bool = True,
                            error_message: Optional[str] = None) -> None:
        """Log configuration generation usage"""
        
        timestamp = datetime.now().isoformat()
        
        # Prepare usage data
        usage_data = {
            'timestamp': timestamp,
            'endpoint': 'generate-config',
            'success': success,
            'plugins': plugins,
            'plugin_count': len(plugins),
            'theme': theme,
            'themes': themes or [],
            'theme_parent': theme_parent,
            'theme_child': theme_child,
            'domain': domain,
            'analyze_domain': analyze_domain,
            'detected_ad_providers': detected_ad_providers or [],
            'ad_providers_count': len(detected_ad_providers) if detected_ad_providers else 0,
            'processing_info': processing_info or {},
            'user_ip': user_ip,
            'user_agent': user_agent,
            'error_message': error_message
        }
        
        # Save to database with config JSON if successful
        config_json = json.dumps(processing_info.get('generated_config')) if processing_info and processing_info.get('generated_config') else None
        self._save_to_database(usage_data, config_json)
        
        # Log to application logs
        if success:
            logger.info(f"Config generated successfully - Plugins: {len(plugins)}, Theme: {theme}, Domain: {domain}")
        else:
            logger.error(f"Config generation failed - Error: {error_message}")
        
        # Send to Slack
        self._send_slack_notification(usage_data)
    
    def log_ad_detection(self,
                        domain: str,
                        detected_providers: List[str],
                        user_ip: Optional[str] = None,
                        success: bool = True,
                        error_message: Optional[str] = None) -> None:
        """Log ad detection usage"""
        
        timestamp = datetime.now().isoformat()
        
        usage_data = {
            'timestamp': timestamp,
            'endpoint': 'detect-ads',
            'success': success,
            'domain': domain,
            'detected_providers': detected_providers,
            'providers_count': len(detected_providers),
            'user_ip': user_ip,
            'error_message': error_message
        }
        
        # Save to database
        self._save_to_database(usage_data)
        
        # Log to application logs
        if success:
            logger.info(f"Ad detection completed - Domain: {domain}, Providers: {detected_providers}")
        else:
            logger.error(f"Ad detection failed - Domain: {domain}, Error: {error_message}")
        
        # Send to Slack (simplified for ad detection)
        self._send_slack_ad_notification(usage_data)
    
    def get_usage_stats_summary(self) -> Dict[str, Any]:
        """Get usage statistics summary"""
        try:
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('''
                        SELECT 
                            COUNT(*) as total_requests,
                            COUNT(CASE WHEN success = 1 THEN 1 END) as successful_requests,
                            COUNT(DISTINCT domain) as unique_domains,
                            COUNT(DISTINCT user_ip) as unique_ips
                        FROM usage_stats 
                        WHERE endpoint = 'generate-config'
                    ''')
                    
                    row = cursor.fetchone()
                    return {
                        'total_requests': row[0] if row else 0,
                        'successful_requests': row[1] if row else 0,
                        'unique_domains': row[2] if row else 0,
                        'unique_ips': row[3] if row else 0
                    }
        except Exception as e:
            logger.error(f"Failed to get usage summary: {e}")
            return {
                'total_requests': 0,
                'successful_requests': 0,
                'unique_domains': 0,
                'unique_ips': 0
            }
    
    def _send_slack_notification(self, usage_data: Dict[str, Any]) -> None:
        """Send usage notification to Slack"""
        
        if not self.slack_webhook_url:
            return
        
        try:
            # Simple message format: Status | Domain | IP | Time
            status = "✓" if usage_data['success'] else "✗"
            domain = usage_data['domain'] or 'No domain'
            ip = usage_data['user_ip'] or 'Unknown IP'
            
            # Format timestamp to readable format
            try:
                dt = datetime.fromisoformat(usage_data['timestamp'].replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = 'Unknown time'
            
            message = f"{status} {domain} | {ip} | {time_str}"
            
            # Add error message if failed
            if not usage_data['success'] and usage_data['error_message']:
                message += f" | Error: {usage_data['error_message'][:100]}"
            
            payload = {
                "channel": self.slack_channel,
                "username": "Perfmatters API",
                "text": message
            }
            
            response = self.requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("Usage notification sent to Slack successfully")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_slack_ad_notification(self, usage_data: Dict[str, Any]) -> None:
        """Send ad detection notification to Slack"""
        
        if not self.slack_webhook_url:
            return
        
        try:
            # Simple ad detection message
            status = "✓" if usage_data['success'] else "✗"
            domain = usage_data['domain'] or 'No domain'
            ip = usage_data['user_ip'] or 'Unknown IP'
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(usage_data['timestamp'].replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except:
                time_str = 'Unknown time'
            
            message = f"{status} [AD] {domain} | {ip} | {time_str}"
            
            if usage_data['success'] and usage_data['detected_providers']:
                message += f" | {len(usage_data['detected_providers'])} providers"
            
            payload = {
                "channel": self.slack_channel,
                "username": "Perfmatters API",
                "text": message
            }
            
            response = self.requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send ad detection Slack notification: {e}")
    
    def log_health_check(self, user_ip: Optional[str] = None) -> None:
        """Log health check (minimal logging)"""
        logger.info(f"Health check from IP: {user_ip or 'Unknown'}")
    
    def log_config_reload(self, user_ip: Optional[str] = None, success: bool = True, error_message: Optional[str] = None) -> None:
        """Log configuration reload"""
        if success:
            logger.info(f"Configuration reloaded successfully from IP: {user_ip or 'Unknown'}")
        else:
            logger.error(f"Configuration reload failed from IP: {user_ip or 'Unknown'} - Error: {error_message}")
        
        # Send simple Slack notification for config reloads
        if self.slack_webhook_url:
            try:
                status = "✓" if success else "✗"
                ip = user_ip or 'Unknown IP'
                
                payload = {
                    "channel": self.slack_channel,
                    "username": "Perfmatters API",
                    "text": f"{status} [RELOAD] Config {'reloaded' if success else 'reload failed'} | {ip}"
                }
                
                self.requests.post(self.slack_webhook_url, json=payload, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send config reload Slack notification: {e}")