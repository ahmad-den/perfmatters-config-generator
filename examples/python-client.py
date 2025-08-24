#!/usr/bin/env python3
"""
Python client example for Perfmatters API
"""

import requests
import json
import sys

class PerfmattersClient:
    def __init__(self, api_url="https://perfmatters.checkmysite.app"):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'PerfmattersClient/1.0'
        })
    
    def health_check(self):
        """Check API health"""
        try:
            response = self.session.get(f"{self.api_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Health check failed: {e}")
            return None
    
    def generate_config(self, plugins, theme, domain=None, analyze_domain=False, output_file=None):
        """Generate Perfmatters configuration"""
        data = {
            "plugins": plugins,
            "theme": theme
        }
        
        if domain:
            data["domain"] = domain
            data["analyze_domain"] = analyze_domain
        
        try:
            response = self.session.post(
                f"{self.api_url}/generate-config",
                json=data
            )
            response.raise_for_status()
            
            # Save to file if output_file is specified
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Configuration saved to {output_file}")
                return True
            else:
                # Return the JSON content
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"Config generation failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Error details: {e.response.text}")
            return None

def main():
    # Initialize client
    client = PerfmattersClient()
    
    # Health check
    print("🔍 Checking API health...")
    health = client.health_check()
    if health:
        print(f"✅ API is healthy: {health}")
    else:
        print("❌ API health check failed")
        sys.exit(1)
    
    # Example 1: Basic configuration
    print("\n📋 Generating basic configuration...")
    success = client.generate_config(
        plugins=["woocommerce", "elementor", "contact-form-7"],
        theme="astra",
        output_file="perfmatters-basic-config.json"
    )
    
    # Example 2: With domain analysis
    print("\n🔍 Generating configuration with domain analysis...")
    success = client.generate_config(
        plugins=["woocommerce", "elementor"],
        theme="astra",
        domain="https://example.com",
        analyze_domain=True,
        output_file="perfmatters-with-ads-config.json"
    )
    
    print("\n🎯 All examples completed!")

if __name__ == "__main__":
    main()