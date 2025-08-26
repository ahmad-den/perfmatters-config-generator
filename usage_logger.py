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
            # Prepare Slack message
            if usage_data['success']:
                color = "good"  # Green
                title = "✅ Perfmatters Config Generated"
                status_emoji = "✅"
            else:
                color = "danger"  # Red
                title = "❌ Config Generation Failed"
                status_emoji = "❌"
            
            # Build plugin list (limit to first 5 for main display)
            plugins_display = usage_data['plugins'][:5]
            remaining_plugins = len(usage_data['plugins']) - 5
            
            plugins_summary = ", ".join(plugins_display)
            if remaining_plugins > 0:
                plugins_summary += f" (+{remaining_plugins} more)"
            
            # Build theme info
            theme_info = []
            if usage_data['theme']:
                theme_info.append(f"Main: {usage_data['theme']}")
            if usage_data['theme_parent']:
                theme_info.append(f"Parent: {usage_data['theme_parent']}")
            if usage_data['theme_child']:
                theme_info.append(f"Child: {usage_data['theme_child']}")
            
            theme_display = " | ".join(theme_info) if theme_info else "None"
            
            # Build ad providers info
            ad_info = ""
            if usage_data['detected_ad_providers']:
                ad_info = f"🎯 {', '.join(usage_data['detected_ad_providers'])}"
            else:
                ad_info = "🔍 None detected"
            
            # Build processing info
            processing_info = usage_data.get('processing_info', {})
            plugins_processed = processing_info.get('plugins_processed', 0)
            themes_processed = processing_info.get('themes_processed', 0)
            
            # Create main attachment with summary
            main_attachment = {
                "color": color,
                "title": title,
                "title_link": usage_data['domain'] if usage_data['domain'] else None,
                "fields": [
                    {
                        "title": "📊 Quick Summary",
                        "value": f"**{usage_data['plugin_count']} plugins** ({plugins_processed} optimized) • **{themes_processed} themes** optimized",
                        "short": True
                    },
                    {
                        "title": "🎯 Ad Detection",
                        "value": ad_info,
                        "short": True
                    },
                    {
                        "title": "🔌 Top Plugins",
                        "value": plugins_summary if usage_data['plugins'] else "None",
                        "short": False
                    }
                ],
                "footer": f"🌐 {usage_data['domain'] or 'No domain'} • 📍 {usage_data['user_ip'] or 'Unknown IP'}",
                "ts": int(datetime.fromisoformat(usage_data['timestamp'].replace('Z', '+00:00')).timestamp())
            }
            
            # Create detailed attachment (collapsed by default)
            details_attachment = {
                "color": "#36a64f" if usage_data['success'] else "#ff0000",
                "title": "📋 Detailed Information",
                "fields": [],
                "footer": "Click to expand for full details"
            }
            
            # Add all plugins if more than 5
            if len(usage_data['plugins']) > 5:
                all_plugins = ", ".join(usage_data['plugins'])
                details_attachment["fields"].append({
                    "title": f"🔌 All {len(usage_data['plugins'])} Plugins",
                    "value": f"```{all_plugins}```",
                    "short": False
                })
            
            # Add theme details
            if theme_display != "None":
                details_attachment["fields"].append({
                    "title": "🎨 Theme Details",
                    "value": theme_display,
                    "short": True
                })
            
            # Add domain analysis details
            if usage_data['analyze_domain']:
                analysis_details = f"**Domain:** {usage_data['domain']}\n**Analysis:** {'✅ Enabled' if usage_data['analyze_domain'] else '❌ Disabled'}"
                if usage_data['detected_ad_providers']:
                    analysis_details += f"\n**Ad Providers:** {', '.join(usage_data['detected_ad_providers'])}"
                
                details_attachment["fields"].append({
                    "title": "🔍 Domain Analysis",
                    "value": analysis_details,
                    "short": True
                })
            
            # Add user agent if available
            if usage_data.get('user_agent') and usage_data['user_agent'] != 'Unknown':
                user_agent_short = usage_data['user_agent'][:100] + "..." if len(usage_data['user_agent']) > 100 else usage_data['user_agent']
                details_attachment["fields"].append({
                    "title": "🖥️ User Agent",
                    "value": f"```{user_agent_short}```",
                    "short": False
                })
            
            # Add error field if failed
            if not usage_data['success'] and usage_data['error_message']:
                main_attachment["fields"].append({
                    "title": "❌ Error",
                    "value": f"```{usage_data['error_message'][:500]}```",
                    "short": False
                })
            
            # Prepare attachments array
            attachments = [main_attachment]
            
            # Only add details attachment if there are details to show
            if details_attachment["fields"]:
                attachments.append(details_attachment)
            
            # Send to Slack
            payload = {
                "channel": self.slack_channel,
                "username": "Perfmatters API",
                "icon_emoji": ":gear:",
                "text": f"{status_emoji} *Perfmatters Configuration Generated*" if usage_data['success'] else f"{status_emoji} *Configuration Generation Failed*",
                "attachments": attachments
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
            if usage_data['success']:
                color = "good" if usage_data['providers_count'] > 0 else "warning"
                title = f"🔍 Ad Detection: {usage_data['providers_count']} providers found"
                emoji = "🎯" if usage_data['providers_count'] > 0 else "🔍"
            else:
                color = "danger"
                title = "❌ Ad Detection Failed"
                emoji = "❌"
            
            attachment = {
                "color": color,
                "title": title,
                "fields": [
                    {
                        "title": "🌐 Domain",
                        "value": usage_data['domain'],
                        "short": True
                    },
                    {
                        "title": "📊 Results",
                        "value": f"*Providers:* {', '.join(usage_data['detected_providers']) if usage_data['detected_providers'] else 'None found'}",
                        "short": True
                    }
                ],
                "footer": f"IP: {usage_data['user_ip'] or 'Unknown'} | {usage_data['timestamp']}",
                "ts": int(datetime.fromisoformat(usage_data['timestamp'].replace('Z', '+00:00')).timestamp())
            }
            
            if not usage_data['success'] and usage_data['error_message']:
                attachment["fields"].append({
                    "title": "❌ Error",
                    "value": f"```{usage_data['error_message'][:300]}```",
                    "short": False
                })
            
            payload = {
                "channel": self.slack_channel,
                "username": "Perfmatters API",
                "icon_emoji": ":mag:",
                "attachments": [attachment]
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
                payload = {
                    "channel": self.slack_channel,
                    "username": "Perfmatters API",
                    "icon_emoji": ":arrows_counterclockwise:",
                    "text": f"{'✅' if success else '❌'} Configuration {'reloaded' if success else 'reload failed'} | IP: {user_ip or 'Unknown'}"
                }
                
                self.requests.post(self.slack_webhook_url, json=payload, timeout=5)
            except Exception as e:
                logger.error(f"Failed to send config reload Slack notification: {e}")