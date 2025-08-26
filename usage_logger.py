import os
import json
import logging
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
        
        # Log to application logs
        if success:
            logger.info(f"Ad detection completed - Domain: {domain}, Providers: {detected_providers}")
        else:
            logger.error(f"Ad detection failed - Domain: {domain}, Error: {error_message}")
        
        # Send to Slack (simplified for ad detection)
        self._send_slack_ad_notification(usage_data)
    
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