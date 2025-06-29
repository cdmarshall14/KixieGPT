import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class KixieAPITester:
    def __init__(self):
        """Initialize with API credentials from environment variables"""
        self.api_key = os.getenv('KIXIE_API_KEY', '0a9e9006077b4048252e8e70f23976ec')
        self.business_id = os.getenv('KIXIE_BUSINESS_ID', '995')
        self.base_url = 'https://apig.kixie.com/app/event'
        
    def test_sms_endpoint(self, target_phone=None, message=None, sender_email=None):
        """Test the Kixie SMS endpoint"""
        
        # Use provided values or defaults
        target_phone = target_phone or os.getenv('TEST_PHONE_NUMBER', '14244854061')
        message = message or f"Test message from HubSpot integration at {datetime.now().strftime('%H:%M:%S')}"
        sender_email = sender_email or os.getenv('SENDER_EMAIL', 'cmarshall@kixie.com')
        
        print("🧪 Testing Kixie SMS API...")
        print("=" * 50)
        print(f"📱 Target: {target_phone}")
        print(f"📧 Sender: {sender_email}")
        print(f"💬 Message: {message}")
        print(f"🏢 Business ID: {self.business_id}")
        print(f"🔑 API Key: {self.api_key[:10]}...")
        
        # Prepare the request
        url = f"{self.base_url}?apikey={self.api_key}&businessid={self.business_id}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            "businessid": self.business_id,
            "email": sender_email,
            "target": target_phone,
            "eventname": "sms",
            "message": message,
            "apikey": self.api_key
        }
        
        print("\n🚀 Making API request...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"\n📊 Response Status: {response.status_code}")
            print(f"📄 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ SUCCESS! SMS API call completed successfully!")
                
                try:
                    response_data = response.json()
                    print(f"📋 Response Data: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📋 Response Text: {response.text}")
                    
                return True
                
            elif response.status_code == 400:
                print("❌ Bad Request (400) - Check your parameters")
                print(f"Response: {response.text}")
                return False
                
            elif response.status_code == 401:
                print("❌ Unauthorized (401) - Check your API key")
                print(f"Response: {response.text}")
                return False
                
            elif response.status_code == 403:
                print("❌ Forbidden (403) - API key doesn't have permission")
                print(f"Response: {response.text}")
                return False
                
            elif response.status_code == 429:
                print("❌ Rate Limited (429) - Too many requests")
                print(f"Response: {response.text}")
                return False
                
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
            return False
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - check internet connection")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def test_with_custom_data(self):
        """Interactive test with custom data"""
        
        print("\n🔧 Custom API Test")
        print("=" * 30)
        
        # Get custom inputs
        phone = input("Enter target phone number (or press Enter for default): ").strip()
        if not phone:
            phone = '14244854061'
        
        message = input("Enter custom message (or press Enter for default): ").strip()
        if not message:
            message = f"Custom test at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        email = input("Enter sender email (or press Enter for default): ").strip()
        if not email:
            email = 'cmarshall@kixie.com'
        
        # Confirm before sending
        print(f"\n📋 Ready to send:")
        print(f"   To: {phone}")
        print(f"   From: {email}")
        print(f"   Message: {message}")
        
        confirm = input("\nSend SMS? (y/N): ").strip().lower()
        
        if confirm == 'y':
            return self.test_sms_endpoint(phone, message, email)
        else:
            print("❌ Test cancelled")
            return False
    
    def validate_configuration(self):
        """Check if all required configuration is present"""
        
        print("🔍 Validating Configuration...")
        
        issues = []
        
        if not self.api_key or self.api_key == 'your_kixie_api_key':
            issues.append("❌ KIXIE_API_KEY not set or using placeholder")
        else:
            print(f"✅ API Key: {self.api_key[:10]}...")
        
        if not self.business_id or self.business_id == 'your_business_id':
            issues.append("❌ KIXIE_BUSINESS_ID not set or using placeholder")
        else:
            print(f"✅ Business ID: {self.business_id}")
        
        test_phone = os.getenv('TEST_PHONE_NUMBER')
        if not test_phone:
            issues.append("⚠️  TEST_PHONE_NUMBER not set (will use default)")
        else:
            print(f"✅ Test Phone: {test_phone}")
        
        sender_email = os.getenv('SENDER_EMAIL')
        if not sender_email:
            issues.append("⚠️  SENDER_EMAIL not set (will use default)")
        else:
            print(f"✅ Sender Email: {sender_email}")
        
        if issues:
            print("\n🔧 Configuration Issues:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print("\n✅ Configuration looks good!")
            return True

def main():
    """Main test function"""
    
    print("🧪 Kixie API Integration Test")
    print("=" * 50)
    
    tester = KixieAPITester()
    
    # Validate configuration
    config_ok = tester.validate_configuration()
    
    if not config_ok:
        print("\n❌ Please fix configuration issues before testing")
        return
    
    print("\nChoose test type:")
    print("1. Quick test with default values")
    print("2. Custom test with your inputs") 
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        print("\n🚀 Running quick test...")
        success = tester.test_sms_endpoint()
        
    elif choice == '2':
        success = tester.test_with_custom_data()
        
    elif choice == '3':
        print("👋 Goodbye!")
        return
        
    else:
        print("❌ Invalid choice")
        return
    
    if success:
        print("\n🎉 API test completed successfully!")
        print("Your Kixie integration is ready to use!")
    else:
        print("\n❌ API test failed. Please check the errors above.")

if __name__ == "__main__":
    main()