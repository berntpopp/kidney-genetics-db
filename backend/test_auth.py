#!/usr/bin/env python3
"""Test authentication endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"

# Test 1: Check if API is running
print("Testing API health...")
response = requests.get(f"{BASE_URL}/health")
print(f"Health check: {response.status_code}")

# Test 2: Try to access public endpoints
print("\nTesting public endpoints...")
response = requests.get(f"{BASE_URL}/api/genes")
print(f"GET /api/genes (public): {response.status_code}")

# Test 3: Test login with admin credentials
print("\nTesting login...")
login_data = {
    "username": "admin",
    "password": "ChangeMe!Admin2024",
    "grant_type": "password"
}
response = requests.post(
    f"{BASE_URL}/api/auth/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
print(f"Login response: {response.status_code}")
if response.status_code == 200:
    tokens = response.json()
    print(f"Access token received: {tokens['access_token'][:20]}...")
    print(f"Token type: {tokens['token_type']}")
    print(f"Expires in: {tokens.get('expires_in', 'N/A')} seconds")
    
    # Test 4: Access protected endpoint with token
    print("\nTesting protected endpoint...")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"GET /api/auth/me: {response.status_code}")
    if response.status_code == 200:
        user_info = response.json()
        print(f"User info: {json.dumps(user_info, indent=2)}")
else:
    print(f"Login failed: {response.text}")

# Test 5: Test public access still works
print("\nVerifying public access still works...")
response = requests.get(f"{BASE_URL}/api/statistics/summary")
print(f"GET /api/statistics/summary (public): {response.status_code}")