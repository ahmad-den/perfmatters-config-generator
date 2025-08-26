import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AdProviderDetector:
    """Detects ad providers from website HTML source and returns appropriate exclusions"""
    
    def __init__(self):
        # Regex for AdThrive subdomain detection
        self.ADTHRIVE_HOST_RE = re.compile(r"https?://([a-z0-9-]+\.)*adthrive\.com/", re.I)
        
        self.ad_providers = {
            "Mediavine": {
                "domains": ["scripts.mediavine.com", "ads.mediavine.com"],
                "patterns": ["window.mediavineDomain", "__mediavineMachine", "mediavine"],
                "js_exclusions": [
                    "mediavine",
                    "mediavine.min.js"
                ],
                "rucss_exclusions": [
                    ".mediavine",
                    ".mediavine-ad",
                    "mediavine.min.css"
                ],
                "delay_js_exclusions": [
                    "mediavine",
                    "mediavine.min.js"
                ],
                "rucss_excluded_selectors": [
                    ".mediavine",
                    ".mediavine-ad"
                ],
                "minify_css_exclusions": [
                    "mediavine.min.css"
                ],
                "minify_js_exclusions": [
                    "mediavine",
                    "mediavine.min.js"
                ]
            },
            "AdThrive/Raptive": {
                "domains": ["adthrive.com", "raptive.com", "raptive.s3", "raptivecdn.com"],
                "patterns": [
                    "window.adthrive",
                    "adthrive.config", 
                    "window.at",
                    "at.siteid",
                    "/sites/",
                    "ads.min.js",
                    "adthrive.com",
                    "raptive"
                ],
                "js_exclusions": [
                    "adthrive",
                    "adthrive.min.js",
                    "ads.min.js"
                ],
                "rucss_exclusions": [
                    ".adthrive",
                    ".adthrive-ad", 
                    "ads.min.css",
                    "adthrive.min.css"
                ],
                "delay_js_exclusions": [
                    "adthrive",
                    "adthrive.min.js",
                    "ads.min.js",
                    "googletag"
                ],
                "rucss_excluded_selectors": [
                    ".adthrive",
                    ".adthrive-ad"
                ],
                "minify_css_exclusions": [
                    "ads.min.css",
                    "adthrive.min.css"
                ],
                "minify_js_exclusions": [
                    "adthrive",
                    "adthrive.min.js",
                    "ads.min.js",
                    "googletag"
                ]
            },
            "Ezoic": {
                "domains": ["www.ezojs.com", "ezoic.com", "ezoic.net"],
                "patterns": ["ezstandalone", "ez_ad_units", "ezoic"],
                "js_exclusions": [
                    "ezoic",
                    "ezoic.min.js"
                ],
                "rucss_exclusions": [
                    ".ezoic",
                    "ezoic.min.css"
                ],
                "delay_js_exclusions": [
                    "ezoic",
                    "ezoic.min.js"
                ],
                "rucss_excluded_selectors": [
                    ".ezoic"
                ],
                "minify_css_exclusions": [
                    "ezoic.min.css"
                ],
                "minify_js_exclusions": [
                    "ezoic",
                    "ezoic.min.js"
                ]
            },
            "Google AdSense": {
                "domains": ["pagead2.googlesyndication.com", "googleadservices.com"],
                "patterns": ["adsbygoogle.push", "(adsbygoogle", "google_ad_client"],
                "js_exclusions": [
                    "adsbygoogle"
                ],
                "rucss_exclusions": [
                    ".adsbygoogle"
                ],
                "delay_js_exclusions": [
                    "adsbygoogle"
                ],
                "rucss_excluded_selectors": [
                    ".adsbygoogle"
                ],
                "minify_css_exclusions": [],
                "minify_js_exclusions": [
                    "adsbygoogle"
                ]
            },
            "Google Ad Manager": {
                "domains": ["securepubads.g.doubleclick.net", "googletagservices.com"],
                "patterns": ["googletag.defineSlot", "googletag.pubads", "gpt.js"],
                "js_exclusions": [
                    "googletag"
                ],
                "rucss_exclusions": [
                    ".googletag"
                ],
                "delay_js_exclusions": [
                    "googletag"
                ],
                "rucss_excluded_selectors": [
                    ".googletag"
                ],
                "minify_css_exclusions": [],
                "minify_js_exclusions": [
                    "googletag"
                ]
            },
            "Amazon Associates": {
                "domains": ["ws-na.amazon-adsystem.com", "amazon-adsystem.com"],
                "patterns": ["amzn_assoc_", "amazon-adsystem"],
                "js_exclusions": [
                    "amazon-adsystem"
                ],
                "rucss_exclusions": [
                    ".amazon-ad"
                ],
                "delay_js_exclusions": [
                    "amazon-adsystem"
                ],
                "rucss_excluded_selectors": [
                    ".amazon-ad"
                ],
                "minify_css_exclusions": [],
                "minify_js_exclusions": [
                    "amazon-adsystem"
                ]
            },
            "Monumetric": {
                "domains": ["d2v734f2ybhd6d.cloudfront.net", "monumetric.com"],
                "patterns": ["MonumetricAds", "monumetric"],
                "js_exclusions": [
                    "monumetric"
                ],
                "rucss_exclusions": [
                    ".monumetric"
                ],
                "delay_js_exclusions": [
                    "monumetric"
                ],
                "rucss_excluded_selectors": [
                    ".monumetric"
                ],
                "minify_css_exclusions": [],
                "minify_js_exclusions": [
                    "monumetric"
                ]
            },
            "Media.net": {
                "domains": ["contextual.media.net", "media.net"],
                "patterns": ["media_net", "media.net"],
                "js_exclusions": [
                    "media_net"
                ],
                "rucss_exclusions": [
                    ".media-net"
                ],
                "delay_js_exclusions": [
                    "media_net"
                ],
                "rucss_excluded_selectors": [
                    ".media-net"
                ],
                "minify_css_exclusions": [],
                "minify_js_exclusions": [
                    "media_net"
                ]
            }
        }
    
    def get_ad_exclusions(self, url: str, timeout: int = 10) -> Dict[str, List[str]]:
        """
        Detect ad providers from a given URL and return exclusions
        
        Args:
            url: The URL to analyze
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with 'rucss_exclusions' and 'delay_js_exclusions' lists
        """
        exclusions = {
            'rucss_exclusions': [],
            'delay_js_exclusions': [],
            'rucss_excluded_selectors': [],
            'minify_css_exclusions': [],
            'js_exclusions': [],
            'minify_js_exclusions': []
        }
        
        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Fetch the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            html_content = response.text
            
            # Parse HTML to extract script sources
            soup = BeautifulSoup(html_content, 'html.parser')
            scripts = soup.find_all('script')
            script_sources = []
            
            for script in scripts:
                if script.get('src'):
                    script_sources.append(script.get('src'))
            
            # Check each ad provider
            for provider_name, provider_config in self.ad_providers.items():
                detected = self._check_provider(html_content, script_sources, provider_config)
                
                if detected:
                    logger.info(f"Ad provider detected: {provider_name}")
                    exclusions['rucss_exclusions'].extend(provider_config.get('rucss_exclusions', []))
                    exclusions['delay_js_exclusions'].extend(provider_config.get('delay_js_exclusions', []))
                    exclusions['rucss_excluded_selectors'].extend(provider_config.get('rucss_excluded_selectors', []))
                    exclusions['minify_css_exclusions'].extend(provider_config.get('minify_css_exclusions', []))
                    exclusions['js_exclusions'].extend(provider_config.get('js_exclusions', []))
                    exclusions['minify_js_exclusions'].extend(provider_config.get('minify_js_exclusions', []))
            
            return exclusions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return exclusions
        except Exception as e:
            logger.error(f"Error analyzing URL {url}: {e}")
            return exclusions
    
    def _check_provider(self, html_content: str, script_sources: List[str], provider_config: Dict) -> bool:
        """
        Check if a specific ad provider is detected
        
        Args:
            html_content: Full HTML content of the page
            script_sources: List of script source URLs
            provider_config: Configuration for the ad provider
            
        Returns:
            True if provider is detected, False otherwise
        """
        html_lower = html_content.lower()
        
        # Check domains and patterns in script sources
        for script_src in script_sources:
            src_lower = script_src.lower()
            
            # Generic domain contains check
            for domain in provider_config["domains"]:
                if domain in src_lower:
                    return True
            
            # Special case: any *.adthrive.com subdomain
            if self.ADTHRIVE_HOST_RE.search(script_src):
                return True
            
            # Common filenames/paths that indicate AdThrive/Raptive
            if "ads.min.js" in src_lower or "/sites/" in src_lower:
                return True
        
        # Check patterns in HTML content
        for pattern in provider_config["patterns"]:
            if pattern.lower() in html_lower:
                return True
        
        return False