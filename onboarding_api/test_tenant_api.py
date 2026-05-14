"""
Test script for Tenant Management API

This script demonstrates how to use the tenant creation endpoint.
Run with: python test_tenant_api.py
"""
import requests
import json
import yaml
import tempfile
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
BEARER_TOKEN = "your-secure-token-here"  # Update this with your token

# Sample YAML configuration for test
SAMPLE_YAML = """
tenant:
  name: "Test Tenant Corp"
  description: "Sample tenant created for testing"
"""


def create_sample_yaml_file():
    """Create a temporary YAML file for testing."""
    temp_dir = tempfile.gettempdir()
    yaml_file = Path(temp_dir) / "test_tenant.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    return str(yaml_file)


def test_tenant_creation():
    """Test the tenant creation endpoint."""
    print("=" * 60)
    print("Testing Tenant Creation API")
    print("=" * 60)
    
    # Create temporary YAML file
    yaml_file = create_sample_yaml_file()
    print(f"\nCreated temporary YAML file: {yaml_file}")
    print(f"YAML Content:\n{SAMPLE_YAML}")
    
    # Prepare request
    url = f"{API_BASE_URL}/api/v1/tenant/create"
    headers = {
        "Authorization": f"Bearer {BEARER_TOKEN}"
    }
    
    print(f"\nSending request to: {url}")
    print(f"Authorization: Bearer {BEARER_TOKEN}")
    
    try:
        # Open and send file
        with open(yaml_file, 'rb') as f:
            files = {'file': ('test_tenant.yaml', f, 'application/x-yaml')}
            response = requests.post(url, headers=headers, files=files)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ SUCCESS! Tenant created:")
            print(json.dumps(data, indent=2))
            
            print("\n" + "=" * 60)
            print("IMPORTANT: Save these credentials securely!")
            print("=" * 60)
            print(f"Tenant PKID:  {data['tenant_pkid']}")
            print(f"Username:     {data['username']}")
            print(f"Password:     {data['password']}")
            print(f"Tenant Name:  {data['tenant_name']}")
            print("=" * 60)
            
        elif response.status_code == 401:
            print("\n❌ ERROR: Unauthorized (Invalid or missing token)")
            print(f"Response: {response.json()}")
            
        elif response.status_code == 409:
            print("\n❌ ERROR: Conflict (Tenant or user already exists)")
            print(f"Response: {response.json()}")
            
        elif response.status_code == 400:
            print("\n❌ ERROR: Bad Request")
            print(f"Response: {response.json()}")
            
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Could not connect to {API_BASE_URL}")
        print("Make sure the FastAPI server is running:")
        print("  uvicorn app:app --reload")
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
    
    finally:
        # Cleanup
        Path(yaml_file).unlink(missing_ok=True)
        print(f"\nCleaned up temporary file: {yaml_file}")


def test_missing_token():
    """Test request without token (should fail)."""
    print("\n\n" + "=" * 60)
    print("Testing Missing Token (Expected to fail)")
    print("=" * 60)
    
    yaml_file = create_sample_yaml_file()
    url = f"{API_BASE_URL}/api/v1/tenant/create"
    
    try:
        with open(yaml_file, 'rb') as f:
            files = {'file': ('test_tenant.yaml', f, 'application/x-yaml')}
            response = requests.post(url, files=files)  # No authorization header
        
        print(f"\nResponse Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly rejected request without token")
        else:
            print(f"⚠️  Unexpected response: {response.json()}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        Path(yaml_file).unlink(missing_ok=True)


def test_invalid_yaml():
    """Test with invalid YAML (should fail)."""
    print("\n\n" + "=" * 60)
    print("Testing Invalid YAML (Expected to fail)")
    print("=" * 60)
    
    # Invalid YAML - missing tenant.name
    invalid_yaml = """
    config:
      invalid: "format"
    """
    
    temp_dir = tempfile.gettempdir()
    yaml_file = Path(temp_dir) / "invalid_tenant.yaml"
    yaml_file.write_text(invalid_yaml)
    
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    url = f"{API_BASE_URL}/api/v1/tenant/create"
    
    try:
        with open(yaml_file, 'rb') as f:
            files = {'file': ('invalid_tenant.yaml', f, 'application/x-yaml')}
            response = requests.post(url, headers=headers, files=files)
        
        print(f"\nResponse Status: {response.status_code}")
        if response.status_code == 400:
            print("✅ Correctly rejected invalid YAML")
            print(f"Response: {response.json()}")
        else:
            print(f"⚠️  Unexpected response: {response.json()}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        yaml_file.unlink(missing_ok=True)


if __name__ == "__main__":
    print("\n🚀 Tenant Management API Test Suite\n")
    print("Before running tests, make sure to:")
    print("1. Start the FastAPI server: uvicorn app:app --reload")
    print("2. Update BEARER_TOKEN in this script with your actual token")
    print("3. Ensure database is initialized\n")
    
    test_tenant_creation()
    test_missing_token()
    test_invalid_yaml()
    
    print("\n\n" + "=" * 60)
    print("Test suite completed!")
    print("=" * 60)
