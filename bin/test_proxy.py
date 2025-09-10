#!/usr/bin/env python3
# coding=utf8

"""
Test script for the SOCKS5 proxy server functionality.
This script can be used to verify the proxy is working correctly.
"""

import requests
import sys
import time
from proxy_server import RinnaProxyServer
import asyncio
import threading
import os


def test_proxy_client(proxy_url: str):
    """Test the proxy by making HTTP requests through it."""
    print(f"Testing proxy: {proxy_url}")
    
    # Configure requests to use the SOCKS5 proxy
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    try:
        # Test HTTP request through proxy
        print("Testing HTTP request through proxy...")
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        # Test HTTPS request through proxy  
        print("\nTesting HTTPS request through proxy...")
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        print("\n✅ Proxy test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False


def test_proxy_authentication():
    """Test proxy authentication by trying both valid and invalid credentials."""
    host = "127.0.0.1"
    port = 1081  # Use different port for testing
    username = "admin"
    password = "test123"
    
    # Start proxy server in background
    proxy_server = RinnaProxyServer(host=host, port=port, username=username, password=password)
    
    def run_proxy():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(proxy_server.start())
        except Exception as e:
            print(f"Proxy server error: {e}")
        finally:
            loop.close()
    
    proxy_thread = threading.Thread(target=run_proxy, daemon=True)
    proxy_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    print("Testing proxy authentication...")
    
    # Test with correct credentials
    proxy_url = f"socks5://{username}:{password}@{host}:{port}"
    print(f"\nTesting with correct credentials: {proxy_url}")
    success = test_proxy_client(proxy_url)
    
    if success:
        print("✅ Authentication test passed")
    else:
        print("❌ Authentication test failed")
    
    # Test with incorrect credentials
    wrong_proxy_url = f"socks5://wrong:credentials@{host}:{port}"
    print(f"\nTesting with incorrect credentials: {wrong_proxy_url}")
    proxies = {'http': wrong_proxy_url, 'https': wrong_proxy_url}
    
    try:
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=5)
        print("❌ Should have failed with wrong credentials")
    except Exception as e:
        print(f"✅ Correctly rejected wrong credentials: {e}")
    
    return success


def main():
    """Main test function."""
    print("SOCKS5 Proxy Server Test")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "auth":
            # Test authentication
            test_proxy_authentication()
        elif sys.argv[1] == "client":
            # Test with existing proxy
            proxy_url = sys.argv[2] if len(sys.argv) > 2 else "socks5://admin:rinna_proxy_2025@127.0.0.1:1080"
            test_proxy_client(proxy_url)
        else:
            print("Usage:")
            print("  python test_proxy.py auth           # Test proxy authentication")
            print("  python test_proxy.py client [url]   # Test proxy client with given URL")
    else:
        # Run both tests
        print("Running authentication test...\n")
        test_proxy_authentication()
        
        print("\n" + "=" * 40)
        print("Test completed!")


if __name__ == "__main__":
    # Add parent directory to path to import proxy_server
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()