#!/usr/bin/env python3
"""
Password Hash Generator for Perfmatters Dashboard

This script generates a secure bcrypt hash for your dashboard password.
Use this hash in your .env file for better security.

Usage:
    python generate_password_hash.py
"""

import bcrypt
import getpass

def generate_password_hash():
    """Generate a secure bcrypt hash for the dashboard password"""
    
    print("🔐 Perfmatters Dashboard Password Hash Generator")
    print("=" * 50)
    print()
    
    # Get password from user (hidden input)
    password = getpass.getpass("Enter your dashboard password: ")
    
    if not password:
        print("❌ Password cannot be empty!")
        return
    
    if len(password) < 8:
        print("⚠️  Warning: Password is less than 8 characters. Consider using a stronger password.")
    
    # Generate salt and hash
    print("\n🔄 Generating secure hash...")
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds is a good balance of security and performance
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    # Display results
    print("\n✅ Password hash generated successfully!")
    print("\n📋 Add this to your .env file:")
    print("-" * 30)
    print(f"DASHBOARD_PASSWORD={password_hash.decode('utf-8')}")
    print("-" * 30)
    
    print("\n🔒 Security Benefits:")
    print("  ✓ Password is not stored in plain text")
    print("  ✓ Uses bcrypt with salt for maximum security")
    print("  ✓ Even if .env file is compromised, password is protected")
    
    print("\n⚠️  Important:")
    print("  • Keep this hash secure and don't share it")
    print("  • If you forget the password, generate a new hash")
    print("  • Restart your application after updating .env")
    
    # Verify the hash works
    print("\n🧪 Testing hash...")
    if bcrypt.checkpw(password.encode('utf-8'), password_hash):
        print("✅ Hash verification successful!")
    else:
        print("❌ Hash verification failed!")

if __name__ == "__main__":
    try:
        generate_password_hash()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")