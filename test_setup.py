import os
import sys
from dotenv import load_dotenv
import mysql.connector
import requests

# Load environment variables
load_dotenv(override=True)  # Force .env to override system variables
def test_environment_variables():
    """Check if all required environment variables are present"""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        'HUBSPOT_API_KEY': 'HubSpot API Key',
        'MYSQL_HOST': 'MySQL Host',
        'MYSQL_USER': 'MySQL Username', 
        'MYSQL_PASSWORD': 'MySQL Password',
        'MYSQL_DATABASE': 'MySQL Database Name',
        'ANTHROPIC_API_KEY': 'Claude API Key'
    }
    
    missing_vars = []
    present_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"   ❌ {var} ({description})")
        else:
            # Show partial value for security
            masked_value = value[:8] + "***" if len(value) > 8 else "***"
            present_vars.append(f"   ✅ {var}: {masked_value}")
    
    print("Present variables:")
    for var in present_vars:
        print(var)
    
    if missing_vars:
        print("\nMissing variables:")
        for var in missing_vars:
            print(var)
        return False
    
    print("\n✅ All environment variables are present!")
    return True

def test_hubspot_connection():
    """Test HubSpot API connection with detailed error info"""
    print("\n🔍 Testing HubSpot API connection...")
    
    api_key = os.getenv('HUBSPOT_API_KEY')
    if not api_key:
        print("❌ No HubSpot API key found in environment")
        return False
    
    # Check API key format
    if not api_key.startswith('pat-'):
        print("⚠️  Warning: HubSpot API key should start with 'pat-'")
        print(f"   Your key starts with: {api_key[:10]}...")
        print("   Make sure you're using a Private App token, not a legacy API key")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    search_payload = {
    'filterGroups': [],
    'properties': ['email', 'firstname', 'lastname'],
    'limit': 1
}
    
    try:
        # Test with a simple endpoint
        response = requests.post(
        'https://api.hubapi.com/crm/v3/objects/contacts/search',
        headers=headers,
        json=search_payload,
        timeout=10
)
        
        if response.status_code == 200:
            print("✅ HubSpot connection successful!")
            data = response.json()
            total = data.get('total', 0)
            print(f"   Found {total} total contacts in your HubSpot")
            return True
        elif response.status_code == 401:
            print("❌ HubSpot authentication failed (401)")
            print("   Possible issues:")
            print("   1. Invalid API key")
            print("   2. API key doesn't have required permissions")
            print("   3. Using old API key format instead of Private App token")
            return False
        elif response.status_code == 403:
            print("❌ HubSpot access forbidden (403)")
            print("   Your API key doesn't have permission to read contacts")
            print("   Add 'crm.objects.contacts.read' scope to your Private App")
            return False
        else:
            print(f"❌ HubSpot API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ HubSpot API timeout - check your internet connection")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ HubSpot API connection error - check your internet connection")
        return False
    except Exception as e:
        print(f"❌ HubSpot API unexpected error: {e}")
        return False

def test_mysql_connection():
    """Test MySQL database connection with detailed error info"""
    print("\n🔍 Testing MySQL database connection...")
    
    # Get configuration
    config = {
        'host': os.getenv('MYSQL_HOST'),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE'),
        'port': int(os.getenv('MYSQL_PORT', 3306))
    }
    
    # Check if all config values are present
    missing_config = [k for k, v in config.items() if not v]
    if missing_config:
        print(f"❌ Missing MySQL configuration: {missing_config}")
        return False
    
    print(f"   Connecting to: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    
    try:
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Test basic query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✅ MySQL connection successful!")
        print(f"   MySQL version: {version}")
        
        # Test database access
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"   Found {len(tables)} tables in database")
        
        cursor.close()
        connection.close()
        return True
        
    except mysql.connector.Error as e:
        error_code = e.errno
        error_msg = e.msg
        
        if error_code == 1045:  # Access denied
            print("❌ MySQL access denied")
            print("   Possible issues:")
            print("   1. Wrong username or password")
            print("   2. Your IP address is not whitelisted")
            print(f"   3. User '{config['user']}' doesn't exist")
            print("   4. User doesn't have permission for this database")
        elif error_code == 2003:  # Can't connect
            print("❌ Cannot connect to MySQL server")
            print("   Possible issues:")
            print("   1. Wrong host address")
            print("   2. Wrong port number")
            print("   3. MySQL server is down")
            print("   4. Firewall blocking connection")
        elif error_code == 1049:  # Unknown database
            print(f"❌ Database '{config['database']}' doesn't exist")
        else:
            print(f"❌ MySQL error {error_code}: {error_msg}")
        
        return False
    except Exception as e:
        print(f"❌ MySQL unexpected error: {e}")
        return False

def test_claude_connection():
    """Test Claude API connection with detailed error info"""
    print("\n🔍 Testing Claude API connection...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ No Claude API key found in environment")
        return False
    
    if not api_key.startswith('sk-ant-'):
        print("⚠️  Warning: Claude API key should start with 'sk-ant-'")
        print(f"   Your key starts with: {api_key[:10]}...")
    
    try:
        import anthropic
        print(f"   Anthropic version: {anthropic.__version__}")
        
        # Clear any environment proxy settings that might interfere
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']
        for var in proxy_vars:
            if var in os.environ:
                print(f"   Warning: Found proxy variable {var}, temporarily removing for test")
                del os.environ[var]
        
        # Initialize client with ONLY the API key parameter
        client = anthropic.Anthropic(
            api_key=api_key
        )
        
        # Test with a simple request using the correct model name
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # Updated to correct model
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        print("✅ Claude API connection successful!")
        print(f"   Response: {response.content[0].text}")
        return True
        
    except ImportError:
        print("❌ Anthropic library not installed")
        print("   Run: pip install anthropic==0.25.1")
        return False
    except TypeError as e:
        if "proxies" in str(e):
            print("❌ Claude API initialization error - proxies issue detected")
            print("   This might be caused by:")
            print("   1. Conflicting environment variables")
            print("   2. Wrong anthropic library version")
            print("   3. Cached pip packages")
            print("   Try: pip uninstall anthropic -y && pip install anthropic==0.25.1")
        else:
            print(f"❌ Claude API type error: {e}")
        return False
    except anthropic.AuthenticationError:
        print("❌ Claude API authentication failed")
        print("   Check your ANTHROPIC_API_KEY")
        return False
    except anthropic.PermissionDeniedError:
        print("❌ Claude API permission denied")
        print("   Your API key doesn't have required permissions")
        return False
    except anthropic.RateLimitError:
        print("❌ Claude API rate limit exceeded")
        print("   Try again in a few minutes")
        return False
    except Exception as e:
        print(f"❌ Claude API error: {e}")
        print(f"   Error type: {type(e).__name__}")
        if "proxies" in str(e):
            print("   This appears to be a proxies-related error")
            print("   Try running: env -i python improved_test_setup.py")
        return False

def main():
    """Run all tests"""
    print("🧪 Running comprehensive connection tests...")
    print("=" * 60)
    
    # Test environment variables first
    if not test_environment_variables():
        print("\n❌ Environment setup incomplete. Please check your .env file.")
        return False
    
    # Test each connection
    results = {
        'hubspot': test_hubspot_connection(),
        'mysql': test_mysql_connection(), 
        'claude': test_claude_connection()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    
    success_count = sum(results.values())
    total_tests = len(results)
    
    for service, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{service.upper():.<20} {status}")
    
    print(f"\nOverall: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("\n🎉 All tests passed! You're ready to use the system!")
        return True
    else:
        print(f"\n❌ {total_tests - success_count} test(s) failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)