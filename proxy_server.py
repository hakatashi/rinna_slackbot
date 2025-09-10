#!/usr/bin/env python3
# coding=utf8

import asyncio
import logging
import os
import sys
from typing import Optional
import pproxy
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class RinnaProxyServer:
    """SOCKS5 proxy server with authentication for the Rinna Slackbot."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 1080, username: str = "admin", password: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password or os.environ.get('PROXY_PASSWORD', 'rinna_proxy_2025')
        self.server = None
        self.running = False
        
    async def start(self):
        """Start the SOCKS5 proxy server with authentication."""
        try:
            # Create SOCKS5 server with username/password authentication
            # Format: socks5://host:port#username:password
            server_uri = f"socks5://{self.host}:{self.port}#{self.username}:{self.password}"
            
            logger.info(f"Starting SOCKS5 proxy server on {self.host}:{self.port}")
            logger.info(f"Authentication: username={self.username}")
            logger.info(f"Server URI: {server_uri}")
            
            # Create the proxy server
            self.server = pproxy.Server(server_uri)
            
            # Start the server
            args = {
                'verbose': logger.info,  # Pass logger for verbose output
                'rserver': [pproxy.Connection('direct://')]  # Use direct connection as remote server
            }
            self.handler = await self.server.start_server(args)
            self.running = True
            logger.info("SOCKS5 proxy server started successfully")
            logger.info(f"Server listening on {self.host}:{self.port}")
            logger.info(f"Client proxy URL: {self.get_proxy_url()}")
            
            # Return the handler so caller can manage the lifecycle if needed
            return self.handler
            
        except Exception as e:
            logger.error(f"Failed to start proxy server: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
            
    async def stop(self):
        """Stop the proxy server."""
        if hasattr(self, 'handler') and self.handler and self.running:
            logger.info("Stopping proxy server...")
            self.handler.close()
            await self.handler.wait_closed()
            self.running = False
            logger.info("Proxy server stopped")
            
    def is_running(self) -> bool:
        """Check if the proxy server is running."""
        return self.running
        
    def get_proxy_url(self) -> str:
        """Get the proxy URL for client configuration (standard format for clients)."""
        return f"socks5://{self.username}:{self.password}@{self.host}:{self.port}"


async def main():
    """Main function to run the proxy server standalone."""
    if len(sys.argv) < 2:
        print("Usage: python proxy_server.py <port> [host] [username] [password]")
        print("Example: python proxy_server.py 1080")
        print("Example: python proxy_server.py 1080 0.0.0.0 admin mypassword")
        sys.exit(1)
        
    port = int(sys.argv[1])
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    username = sys.argv[3] if len(sys.argv) > 3 else "admin"
    password = sys.argv[4] if len(sys.argv) > 4 else None
    
    if password is None:
        password = os.environ.get('PROXY_PASSWORD', 'rinna_proxy_2025')
    
    # Use RinnaProxyServer class
    proxy_server = RinnaProxyServer(host=host, port=port, username=username, password=password)
    
    logger.info(f"Proxy URL: {proxy_server.get_proxy_url()}")
    
    try:
        handler = await proxy_server.start()
        logger.info("Proxy server handler started")
        
        # Keep server running until interrupted
        try:
            # Create a future that never completes to keep server running
            forever = asyncio.get_event_loop().create_future()
            await forever
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Received interrupt signal")
        finally:
            await proxy_server.stop()
            
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProxy server stopped by user")
    except Exception as e:
        print(f"Failed to start proxy server: {e}")