import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(override=True)

def test_hubspot_data_access():
    """Test different HubSpot endpoints to diagnose data access issues"""
    
    api_key = os.getenv('HUBSPOT_API_KEY')
    if not api_key:
        print("❌ No HubSpot API key found")
        return
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("🔍 HubSpot Data Access Diagnostic")
    print("=" * 60)
    print(f"🔑 Using API key: {api_key[:25]}...")
    
    # Test 1: Account Information
    print("\n1️⃣ ACCOUNT INFORMATION")
    print("-" * 30)
    
    try:
        response = requests.get('https://api.hubapi.com/account-info/v3/details', headers=headers)
        if response.status_code == 200:
            account = response.json()
            print(f"✅ Portal ID: {account.get('portalId')}")
            print(f"✅ Account Name: {account.get('accountName')}")
            print(f"✅ Domain: {account.get('domain')}")
            print(f"✅ Hub ID: {account.get('hubId')}")
            print(f"✅ Account Type: {account.get('accountType')}")
        else:
            print(f"❌ Cannot get account info: {response.status_code}")
    except Exception as e:
        print(f"❌ Account info error: {e}")
    
    # Test 2: Private App Scopes
    print("\n2️⃣ PRIVATE APP SCOPES")
    print("-" * 30)
    
    try:
        # Try to get app info (this might not work for all keys)
        response = requests.get('https://api.hubapi.com/oauth/v1/access-tokens/' + api_key.split('-')[-1], headers=headers)
        if response.status_code == 200:
            token_info = response.json()
            scopes = token_info.get('scopes', [])
            print("✅ Your app has these scopes:")
            for scope in scopes:
                print(f"   • {scope}")
        else:
            print("⚠️  Cannot retrieve scope info directly")
    except Exception as e:
        print(f"⚠️  Scope check not available: {e}")
    
    # Test 3: CRM Object Counts
    print("\n3️⃣ CRM OBJECT COUNTS")
    print("-" * 30)
    
    crm_objects = [
        ('contacts', 'Contacts'),
        ('companies', 'Companies'), 
        ('deals', 'Deals'),
        ('tickets', 'Tickets'),
        ('products', 'Products'),
        ('line_items', 'Line Items'),
        ('quotes', 'Quotes')
    ]
    
    working_objects = []
    
    for obj_type, display_name in crm_objects:
        try:
            url = f'https://api.hubapi.com/crm/v3/objects/{obj_type}?limit=1'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                results_count = len(data.get('results', []))
                
                if total > 0:
                    print(f"✅ {display_name}: {total:,} total records")
                    working_objects.append(obj_type)
                    
                    # Show sample record
                    if results_count > 0:
                        sample = data['results'][0]
                        sample_id = sample.get('id', 'No ID')
                        created = sample.get('createdAt', 'No date')
                        print(f"   📄 Sample: ID {sample_id}, Created: {created}")
                else:
                    print(f"⚠️  {display_name}: 0 records found")
                    
            elif response.status_code == 403:
                print(f"❌ {display_name}: Permission denied (403)")
            else:
                print(f"❌ {display_name}: Error {response.status_code}")
                
        except Exception as e:
            print(f"❌ {display_name}: Exception - {e}")
    
    # Test 4: Contacts with Different Parameters
    print("\n4️⃣ CONTACTS DETAILED ANALYSIS")
    print("-" * 30)
    
    contact_tests = [
        {
            'name': 'All contacts (default)',
            'url': 'https://api.hubapi.com/crm/v3/objects/contacts',
            'params': {'limit': 10}
        },
        {
            'name': 'All contacts (with properties)',
            'url': 'https://api.hubapi.com/crm/v3/objects/contacts',
            'params': {'limit': 10, 'properties': 'email,firstname,lastname,createdate'}
        },
        {
            'name': 'Recently created contacts',
            'url': 'https://api.hubapi.com/crm/v3/objects/contacts',
            'params': {
                'limit': 10,
                'properties': 'email,firstname,lastname,createdate',
                'sorts': 'createdate'
            }
        },
        {
            'name': 'Recently modified contacts',
            'url': 'https://api.hubapi.com/crm/v3/objects/contacts',
            'params': {
                'limit': 10,
                'properties': 'email,firstname,lastname,lastmodifieddate',
                'sorts': 'lastmodifieddate'
            }
        }
    ]
    
    for test in contact_tests:
        try:
            response = requests.get(test['url'], headers=headers, params=test['params'])
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                results = data.get('results', [])
                
                print(f"✅ {test['name']}: {total:,} total, {len(results)} returned")
                
                if results:
                    # Show details of first contact
                    contact = results[0]
                    props = contact.get('properties', {})
                    print(f"   📧 Sample: {props.get('email', 'No email')}")
                    print(f"   👤 Name: {props.get('firstname', '')} {props.get('lastname', '')}")
                    print(f"   📅 Created: {props.get('createdate', 'Unknown')}")
                    
            else:
                print(f"❌ {test['name']}: Error {response.status_code}")
                if response.status_code == 403:
                    print("   Missing permissions for this request")
                    
        except Exception as e:
            print(f"❌ {test['name']}: Exception - {e}")
    
    # Test 5: Contact Search API
    print("\n5️⃣ CONTACT SEARCH API")
    print("-" * 30)
    
    search_tests = [
        {
            'name': 'Search all contacts (no filters)',
            'payload': {
                'filterGroups': [],
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}],
                'properties': ['email', 'firstname', 'lastname', 'createdate'],
                'limit': 5
            }
        },
        {
            'name': 'Search contacts with email',
            'payload': {
                'filterGroups': [
                    {
                        'filters': [
                            {
                                'propertyName': 'email',
                                'operator': 'HAS_PROPERTY'
                            }
                        ]
                    }
                ],
                'properties': ['email', 'firstname', 'lastname'],
                'limit': 5
            }
        }
    ]
    
    for test in search_tests:
        try:
            response = requests.post(
                'https://api.hubapi.com/crm/v3/objects/contacts/search',
                headers=headers,
                json=test['payload']
            )
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                results = data.get('results', [])
                
                print(f"✅ {test['name']}: {total:,} total")
                
                if results:
                    for i, contact in enumerate(results[:3], 1):
                        props = contact.get('properties', {})
                        email = props.get('email', 'No email')
                        name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                        print(f"   {i}. {email} ({name or 'No name'})")
                        
            else:
                print(f"❌ {test['name']}: Error {response.status_code}")
                
        except Exception as e:
            print(f"❌ {test['name']}: Exception - {e}")
    
    # Test 6: Check for Archived/Deleted Contacts
    print("\n6️⃣ ARCHIVED/DELETED CONTACTS")
    print("-" * 30)
    
    try:
        # Check if there are archived contacts
        response = requests.get(
            'https://api.hubapi.com/crm/v3/objects/contacts',
            headers=headers,
            params={'limit': 1, 'archived': 'true'}
        )
        
        if response.status_code == 200:
            data = response.json()
            archived_total = data.get('total', 0)
            print(f"📦 Archived contacts: {archived_total:,}")
        else:
            print(f"⚠️  Cannot check archived contacts: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Archived check error: {e}")
    
    # Summary and Recommendations
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if working_objects:
        print(f"✅ Objects with data: {', '.join(working_objects)}")
    else:
        print("❌ No CRM objects found with data")
    
    print("\n🔧 RECOMMENDATIONS:")
    
    if 'contacts' not in working_objects:
        print("📋 For Contacts (0 found):")
        print("   1. Check if you're in the right HubSpot portal")
        print("   2. Verify your Private App has 'crm.objects.contacts.read' scope")
        print("   3. Check if contacts exist in HubSpot web interface")
        print("   4. Look for contacts in different views/lists")
        print("   5. Check if contacts are archived or in a different database")
        
    if working_objects:
        print(f"\n✅ Good news: You have access to {len(working_objects)} object types")
        print("   You can work with the available data while fixing contacts")
        
    print("\n🌐 Next Steps:")
    print("   1. Log into HubSpot web interface and verify contact count")
    print("   2. Check your Private App permissions")
    print("   3. Try importing/creating test contacts if none exist")

if __name__ == "__main__":
    test_hubspot_data_access()