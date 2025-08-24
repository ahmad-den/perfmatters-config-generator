#!/usr/bin/env python3
"""
Test script for the Perfmatters Configuration Generator API
"""

import requests
import json
import sys

def test_api():
    """Test the API endpoints"""
    base_url = "http://localhost:8080"
    
    print("Testing Perfmatters Configuration Generator API...")
    print("-" * 50)
    
    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Connection failed. Is the server running?")
        sys.exit(1)
    
    print()
    
    # Test config generation without domain analysis
    print("2. Testing config generation (basic)...")
    test_data = {
        "plugins": ["woocommerce", "elementor", "contact-form-7"],
        "theme": "astra"
    }
    
    try:
        response = requests.post(
            f"{base_url}/generate-config",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Basic config generation passed")
            print(f"   Plugins processed: {result['processing_info']['plugins_processed']}")
            print(f"   Theme processed: {result['processing_info']['theme_processed']}")
        else:
            print(f"✗ Basic config generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"✗ Basic config generation error: {e}")
    
    print()
    
    # Test config generation with domain analysis
    print("3. Testing config reload...")
    try:
        response = requests.post(f"{base_url}/reload-config")
        if response.status_code == 200:
            print("✓ Config reload passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"✗ Config reload failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Config reload error: {e}")
    
    print()
    
    # Test error handling
    print("4. Testing error handling...")
    try:
        response = requests.post(
            f"{base_url}/generate-config",
            json={"invalid": "data"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 400:
            print("✓ Error handling passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"✗ Error handling failed: expected 400, got {response.status_code}")
    except Exception as e:
        print(f"✗ Error handling test error: {e}")
    
    print()
    print("API testing completed!")

if __name__ == "__main__":
    test_api()