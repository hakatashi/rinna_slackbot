#!/usr/bin/env node

/**
 * JavaScript test script for the SOCKS5 proxy server functionality.
 * Tests the proxy using axios with axios-socks5-agent.
 * 
 * Usage: node test_proxy.js
 */

const axios = require('axios');
const { SocksProxyAgent } = require('socks-proxy-agent');

// Proxy configuration
const PROXY_HOST = '127.0.0.1';  // Changed from 0.0.0.0 to 127.0.0.1
const PROXY_PORT = 1080;  // Updated to test new server
const PROXY_USERNAME = 'admin';
const PROXY_PASSWORD = 'TwlNcsmk5MyaVXva';

// Create SOCKS5 proxy URL
const proxyUrl = `socks5://${PROXY_USERNAME}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}`;

console.log('SOCKS5 Proxy Test (JavaScript)');
console.log('=====================================');
console.log(`Testing proxy: ${proxyUrl}`);

async function testProxyConnection() {
    try {
        // Create SOCKS5 proxy agent using socks-proxy-agent
        const agent = new SocksProxyAgent(proxyUrl);
        
        // Configure axios with the SOCKS5 agent
        const axiosInstance = axios.create({
            httpsAgent: agent,
            httpAgent: agent,
            timeout: 10000
        });

        console.log('\nTesting HTTP request through proxy...');
        
        // Test HTTP request
        const httpResponse = await axiosInstance.get('http://httpbin.org/ip');
        console.log(`✅ HTTP Response status: ${httpResponse.status}`);
        console.log(`   Response data: ${JSON.stringify(httpResponse.data, null, 2)}`);

        console.log('\nTesting HTTPS request through proxy...');
        
        // Test HTTPS request
        const httpsResponse = await axiosInstance.get('https://httpbin.org/ip');
        console.log(`✅ HTTPS Response status: ${httpsResponse.status}`);
        console.log(`   Response data: ${JSON.stringify(httpsResponse.data, null, 2)}`);

        console.log('\n✅ All proxy tests successful!');
        console.log('🎉 SOCKS5 proxy is working correctly with JavaScript/Node.js');
        
        return true;
        
    } catch (error) {
        console.error('❌ Proxy test failed:');
        console.error(`   Error: ${error.message}`);
        
        if (error.code) {
            console.error(`   Error code: ${error.code}`);
        }
        
        if (error.response) {
            console.error(`   Response status: ${error.response.status}`);
            console.error(`   Response data: ${JSON.stringify(error.response.data, null, 2)}`);
        }
        
        return false;
    }
}

async function testWithoutProxy() {
    try {
        console.log('\n📍 Testing direct connection (without proxy)...');
        
        const response = await axios.get('http://httpbin.org/ip', { timeout: 5000 });
        console.log(`   Direct IP: ${response.data.origin}`);
        
    } catch (error) {
        console.error(`   Direct connection failed: ${error.message}`);
    }
}

async function testProxyAuthentication() {
    console.log('\n🔐 Testing proxy authentication...');
    
    try {
        // Test with correct credentials
        console.log('   Testing with correct credentials...');
        const correctAgent = new SocksProxyAgent(proxyUrl);
        const correctAxios = axios.create({
            httpAgent: correctAgent,
            httpsAgent: correctAgent,
            timeout: 5000
        });
        
        await correctAxios.get('http://httpbin.org/ip');
        console.log('   ✅ Authentication with correct credentials: SUCCESS');
        
    } catch (error) {
        console.error('   ❌ Authentication with correct credentials: FAILED');
        console.error(`      Error: ${error.message}`);
    }
    
    try {
        // Test with incorrect credentials
        console.log('   Testing with incorrect credentials...');
        const wrongProxyUrl = `socks5://wrong:credentials@${PROXY_HOST}:${PROXY_PORT}`;
        const wrongAgent = new SocksProxyAgent(wrongProxyUrl);
        const wrongAxios = axios.create({
            httpAgent: wrongAgent,
            httpsAgent: wrongAgent,
            timeout: 5000
        });
        
        await wrongAxios.get('http://httpbin.org/ip');
        console.error('   ❌ Authentication should have failed with wrong credentials');
        
    } catch (error) {
        console.log('   ✅ Authentication correctly rejected wrong credentials');
        console.log(`      Error: ${error.message}`);
    }
}

async function main() {
    console.log(`Node.js version: ${process.version}`);
    console.log('axios: using CommonJS require');
    console.log('socks-proxy-agent: using CommonJS require');
    
    // Run all tests
    await testWithoutProxy();
    
    const proxyWorking = await testProxyConnection();
    
    if (proxyWorking) {
        await testProxyAuthentication();
    }
    
    console.log('\n=====================================');
    if (proxyWorking) {
        console.log('🎯 Overall result: PROXY IS WORKING');
        process.exit(0);
    } else {
        console.log('💥 Overall result: PROXY FAILED');
        process.exit(1);
    }
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
});

// Run the test
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});