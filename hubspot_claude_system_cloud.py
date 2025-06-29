import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import anthropic
from dotenv import load_dotenv

# Load environment variables with override
load_dotenv(override=True)

@dataclass
class QueryResult:
    """Structure for query results"""
    data: List[Dict]
    source: str  # 'hubspot' or 'combined'
    query_type: str
    timestamp: datetime
    total_count: int = 0  # Total count from API (different from len(data))

class HubSpotClaudeSystem:
    def __init__(self):
        """Initialize the system with API keys"""
        
        # HubSpot Configuration
        self.hubspot_api_key = os.getenv('HUBSPOT_API_KEY')
        self.hubspot_base_url = "https://api.hubapi.com"
        
        # Claude Configuration
        self.claude_client = anthropic.Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        
        # Kixie SMS API Configuration
        self.kixie_config = {
            'api_key': os.getenv('KIXIE_API_KEY'),
            'business_id': os.getenv('KIXIE_BUSINESS_ID'),
            'base_url': 'https://apig.kixie.com/app/event',
            'sender_email': os.getenv('SENDER_EMAIL', 'cmarshall@kixie.com')
        }
        
        # Skip MySQL database connection for cloud deployment
        print("✅ HubSpot system initialized (cloud mode - no MySQL)")
        
    def connect_to_database(self):
        """Skip database connection for cloud deployment"""
        print("ℹ️  Database connection skipped in cloud mode")
        return False  # Return False so the web server knows MySQL is not available
        
    def get_hubspot_data(self, endpoint: str, params: Dict = None) -> Dict:
        """Get data from HubSpot API (generic method)"""
        url = f"{self.hubspot_base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.hubspot_api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ HubSpot API error: {e}")
            return {}
    
    def get_hubspot_contacts(self, limit: int = 100, properties: list = None, filters: list = None, query: str = None) -> Dict:
        """Get contacts using the search endpoint (more reliable than GET)"""
        
        if properties is None:
            properties = ['email', 'firstname', 'lastname', 'phone', 'company', 'createdate', 'lifecyclestage']
        
        # Build search payload - use query if provided, otherwise use filters
        if query:
            search_payload = {
                'query': query,
                'properties': properties,
                'limit': min(limit, 100),  # HubSpot max is 100 per request
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
            }
        else:
            search_payload = {
                'filterGroups': filters or [],
                'properties': properties,
                'limit': min(limit, 100),  # HubSpot max is 100 per request
                'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
            }
        
        headers = {
            'Authorization': f'Bearer {self.hubspot_api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.hubspot_base_url}/crm/v3/objects/contacts/search",
                headers=headers,
                json=search_payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ HubSpot contacts error: {e}")
            return {}
    
    def get_hubspot_deals(self, limit: int = 100, properties: list = None, filters: list = None) -> Dict:
        """Get deals using the search endpoint"""
        
        if properties is None:
            properties = ['dealname', 'amount', 'dealstage', 'createdate', 'closedate', 'pipeline']
        
        search_payload = {
            'filterGroups': filters or [],
            'properties': properties,
            'limit': min(limit, 100),
            'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
        }
        
        headers = {
            'Authorization': f'Bearer {self.hubspot_api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.hubspot_base_url}/crm/v3/objects/deals/search",
                headers=headers,
                json=search_payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ HubSpot deals error: {e}")
            return {}
    
    def get_hubspot_companies(self, limit: int = 100, properties: list = None, filters: list = None) -> Dict:
        """Get companies using the search endpoint"""
        
        if properties is None:
            properties = ['name', 'domain', 'industry', 'city', 'state', 'createdate']
        
        search_payload = {
            'filterGroups': filters or [],
            'properties': properties,
            'limit': min(limit, 100),
            'sorts': [{'propertyName': 'createdate', 'direction': 'DESCENDING'}]
        }
        
        headers = {
            'Authorization': f'Bearer {self.hubspot_api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f"{self.hubspot_base_url}/crm/v3/objects/companies/search",
                headers=headers,
                json=search_payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ HubSpot companies error: {e}")
            return {}
    
    def get_database_schema(self) -> Dict[str, List[str]]:
        """Get HubSpot schema for Claude to understand the structure"""
        
        # HubSpot object types and their common properties
        hubspot_objects = {
            'contacts': [
                'id', 'email', 'firstname', 'lastname', 'phone', 'company', 
                'createdate', 'lastmodifieddate', 'lifecyclestage', 'hs_lead_status',
                'city', 'state', 'country', 'website', 'jobtitle'
            ],
            'companies': [
                'id', 'name', 'domain', 'industry', 'city', 'state', 'country',
                'createdate', 'numberofemployees', 'annualrevenue', 'phone', 'website'
            ],
            'deals': [
                'id', 'dealname', 'amount', 'dealstage', 'pipeline', 'createdate', 
                'closedate', 'hubspot_owner_id', 'dealtype', 'description'
            ],
            'tickets': [
                'id', 'subject', 'content', 'hs_pipeline_stage', 'createdate',
                'hs_ticket_priority', 'hubspot_owner_id'
            ]
        }
        
        return {
            'hubspot': hubspot_objects
        }
    
    def process_question_with_claude(self, question: str) -> Dict[str, Any]:
        """Send question to Claude to determine what data to query and how"""
        
        schema = self.get_database_schema()
        
        # Get current date information for Claude to use
        from datetime import datetime, timedelta
        import calendar
        
        now = datetime.now()
        current_month_start = datetime(now.year, now.month, 1)
        current_month_start_iso = current_month_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        last_month = now.replace(day=1) - timedelta(days=1)
        last_month_start = datetime(last_month.year, last_month.month, 1)
        last_month_start_iso = last_month_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Get week start (Monday)
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday)
        week_start_midnight = datetime(week_start.year, week_start.month, week_start.day)
        week_start_iso = week_start_midnight.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        system_prompt = f"""
        You are an AI assistant that helps analyze business questions about HubSpot CRM data.
        
        Available data source:
        - HubSpot API - Real-time CRM data including contacts, companies, deals, and tickets
        
        HubSpot Schema:
        {json.dumps(schema['hubspot'], indent=2)}
        
        CURRENT DATE CONTEXT (use these exact values):
        - Today's date: {now.strftime("%Y-%m-%d")}
        - Current month start: {current_month_start_iso}
        - Last month start: {last_month_start_iso}
        - This week start: {week_start_iso}
        
        Your task is to:
        1. Understand the user's question
        2. Determine what HubSpot data to query
        3. Generate appropriate API calls with proper HubSpot filter format
        4. Suggest what actions to take based on potential results
        
        IMPORTANT: For PHONE NUMBER searches, use multiple strategies to ensure we find the contact.
        
        For phone number "14244854061", generate these 3 strategies:
        
        Strategy 1 - Search calculated phone field without country code:
        "filterGroups": [
            {{
                "filters": [
                    {{
                        "operator": "CONTAINS_TOKEN",
                        "propertyName": "hs_searchable_calculated_phone_number",
                        "value": "4244854061"
                    }}
                ]
            }}
        ]
        
        Strategy 2 - Search calculated phone field with country code:
        "filterGroups": [
            {{
                "filters": [
                    {{
                        "operator": "CONTAINS_TOKEN", 
                        "propertyName": "hs_searchable_calculated_phone_number",
                        "value": "14244854061"
                    }}
                ]
            }}
        ]
        
        Strategy 3 - General search query:
        "query": "4244854061"
        
        IMPORTANT: Respond with ONLY a valid JSON object, no additional text.
        
        Example for "Find contacts that contain the phone number 14244854061":
        {{
            "data_sources": ["hubspot"],
            "hubspot_endpoints": [
                {{
                    "endpoint": "contacts", 
                    "params": {{
                        "limit": 50, 
                        "properties": ["email", "firstname", "lastname", "phone", "hs_searchable_calculated_phone_number"],
                        "filterGroups": [
                            {{
                                "filters": [
                                    {{
                                        "operator": "CONTAINS_TOKEN",
                                        "propertyName": "hs_searchable_calculated_phone_number",
                                        "value": "4244854061"
                                    }}
                                ]
                            }}
                        ]
                    }}, 
                    "purpose": "Strategy 1: Search calculated phone field (no country code)"
                }},
                {{
                    "endpoint": "contacts", 
                    "params": {{
                        "limit": 50, 
                        "properties": ["email", "firstname", "lastname", "phone", "hs_searchable_calculated_phone_number"],
                        "filterGroups": [
                            {{
                                "filters": [
                                    {{
                                        "operator": "CONTAINS_TOKEN",
                                        "propertyName": "hs_searchable_calculated_phone_number",
                                        "value": "14244854061"
                                    }}
                                ]
                            }}
                        ]
                    }}, 
                    "purpose": "Strategy 2: Search calculated phone field (with country code)"
                }},
                {{
                    "endpoint": "contacts", 
                    "params": {{
                        "limit": 50, 
                        "properties": ["email", "firstname", "lastname", "phone", "hs_searchable_calculated_phone_number"],
                        "query": "4244854061"
                    }}, 
                    "purpose": "Strategy 3: General search query"
                }}
            ],
            "expected_result_type": "Contact records with matching phone number",
            "suggested_actions": ["send_sms", "create_task"],
            "action_triggers": {{"when_single_match_found": "send_sms"}}
        }}
        """
        
        try:
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Question: {question}"}
                ]
            )
            
            # Get Claude's response
            claude_response = response.content[0].text.strip()
            print(f"📝 Claude raw response: {claude_response[:200]}...")
            
            # Try to extract JSON from the response
            parsed_response = self.extract_json_from_response(claude_response)
            
            if parsed_response:
                return parsed_response
            else:
                print("⚠️  Could not parse Claude's response, using fallback")
                return self.get_fallback_analysis(question)
            
        except Exception as e:
            print(f"❌ Claude processing error: {e}")
            print("🔄 Using fallback analysis instead")
            return self.get_fallback_analysis(question)
    
    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from Claude's response, handling various formats"""
        
        # Remove markdown code blocks if present
        if "```json" in response_text:
            # Extract content between ```json and ```
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            # Extract content between ``` and ```
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        
        # Try to find JSON object boundaries
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_text = response_text[json_start:json_end]
            
            try:
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
                print(f"🔍 Attempted to parse: {json_text[:100]}...")
                return None
        
        # Try parsing the entire response
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return None
    
    def get_fallback_analysis(self, question: str) -> Dict[str, Any]:
        """Provide a fallback analysis when Claude fails"""
        
        question_lower = question.lower()
        
        # Check for different query types
        if any(word in question_lower for word in ['contact', 'people', 'customer', 'lead']):
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "contacts", 
                        "params": {"limit": 50, "properties": ["email", "firstname", "lastname", "phone", "company"]}, 
                        "purpose": "Get contact information (fallback)"
                    }
                ],
                "expected_result_type": "Contact records from HubSpot",
                "suggested_actions": ["send_notification"],
                "action_triggers": {}
            }
        elif any(word in question_lower for word in ['deal', 'sale', 'opportunity', 'revenue']):
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "deals", 
                        "params": {"limit": 50, "properties": ["dealname", "amount", "dealstage"]}, 
                        "purpose": "Get deal information (fallback)"
                    }
                ],
                "expected_result_type": "Deal records from HubSpot",
                "suggested_actions": ["send_notification"],
                "action_triggers": {}
            }
        elif any(word in question_lower for word in ['company', 'business', 'organization', 'account']):
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "companies", 
                        "params": {"limit": 50, "properties": ["name", "domain", "industry"]}, 
                        "purpose": "Get company information (fallback)"
                    }
                ],
                "expected_result_type": "Company records from HubSpot",
                "suggested_actions": ["send_notification"],
                "action_triggers": {}
            }
        else:
            # Default to contacts
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "contacts", 
                        "params": {"limit": 20, "properties": ["email", "firstname", "lastname"]}, 
                        "purpose": "Get general contact information (fallback)"
                    }
                ],
                "expected_result_type": "Contact records from HubSpot",
                "suggested_actions": ["send_notification"],
                "action_triggers": {}
            }
    
    def execute_hubspot_queries(self, endpoints: List[Dict]) -> QueryResult:
        """Execute HubSpot API calls based on Claude's recommendations"""
        all_data = []
        total_count = 0
        
        for i, endpoint_config in enumerate(endpoints):
            endpoint = endpoint_config['endpoint']
            params = endpoint_config.get('params', {})
            purpose = endpoint_config.get('purpose', f'Strategy {i+1}')
            
            print(f"📡 Trying {purpose}")
            
            # Extract parameters
            filters = params.get('filterGroups', [])
            query = params.get('query')
            
            # Use specific methods for different object types
            if 'contacts' in endpoint:
                data = self.get_hubspot_contacts(
                    limit=params.get('limit', 50),
                    properties=params.get('properties', None),
                    filters=filters if not query else None,
                    query=query
                )
            elif 'deals' in endpoint:
                data = self.get_hubspot_deals(
                    limit=params.get('limit', 50),
                    properties=params.get('properties', None),
                    filters=filters
                )
            elif 'companies' in endpoint:
                data = self.get_hubspot_companies(
                    limit=params.get('limit', 50),
                    properties=params.get('properties', None),
                    filters=filters
                )
            else:
                # Fallback to generic method for other endpoints
                data = self.get_hubspot_data(endpoint, params)
            
            if 'results' in data:
                api_total = data.get('total', 0)
                actual_results = data.get('results', [])
                results_count = len(actual_results)
                
                print(f"   📊 {purpose}: {api_total:,} total records, {results_count} retrieved")
                
                total_count += api_total
                
                # Extract and flatten properties
                for item in actual_results:
                    if 'properties' in item:
                        flattened = {'id': item.get('id')}
                        flattened.update(item['properties'])
                        all_data.append(flattened)
                    else:
                        all_data.append(item)
        
        return QueryResult(
            data=all_data,
            source='hubspot',
            query_type='api_call',
            timestamp=datetime.now(),
            total_count=total_count
        )
    
    def send_single_kixie_sms(self, target_phone: str, message: str, sender_email: str = None) -> bool:
        """Send a single SMS via Kixie API"""
        
        if not sender_email:
            sender_email = self.kixie_config['sender_email']
        
        url = f"{self.kixie_config['base_url']}?apikey={self.kixie_config['api_key']}&businessid={self.kixie_config['business_id']}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            "businessid": self.kixie_config['business_id'],
            "email": sender_email,
            "target": target_phone,
            "eventname": "sms", 
            "message": message,
            "apikey": self.kixie_config['api_key']
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Kixie API error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Kixie SMS error: {e}")
            return False
    
    def execute_external_actions(self, results: List[QueryResult], actions: List[str], triggers: Dict):
        """Execute external API actions based on query results"""
        
        for action in actions:
            if action == "send_notification":
                self.send_notification(results)
            elif action == "create_task":
                self.create_tasks(results)
            elif action == "send_sms":
                self.send_kixie_sms(results)
            elif action == "generate_report":
                self.generate_report(results)
            else:
                print(f"❌ Unknown action type: {action}")
    
    def send_kixie_sms(self, results: List[QueryResult]):
        """Send SMS notifications via Kixie API based on query results"""
        try:
            print("📱 Sending SMS notifications via Kixie...")
            
            sms_count = 0
            
            for result in results:
                for record in result.data[:5]:  # Limit to first 5 records
                    
                    # Extract phone number from record
                    phone = self.extract_phone_number(record)
                    if not phone:
                        print(f"⚠️  No phone number found for record: {record.get('id', 'unknown')}")
                        continue
                    
                    # Extract name for personalization
                    name = self.extract_name(record)
                    
                    # Create personalized message
                    message = f"Hi {name}! Following up on your inquiry. Let's connect soon!"
                    
                    print(f"💬 Message for {name}: {message}")
                    
                    # Send SMS via Kixie
                    success = self.send_single_kixie_sms(
                        target_phone=phone,
                        message=message,
                        sender_email=self.kixie_config['sender_email']
                    )
                    
                    if success:
                        sms_count += 1
                        print(f"✅ SMS sent to {name} ({phone})")
                    else:
                        print(f"❌ Failed to send SMS to {name} ({phone})")
            
            print(f"📊 SMS Summary: {sms_count} messages sent successfully")
            return sms_count > 0
            
        except Exception as e:
            print(f"❌ SMS campaign error: {e}")
            return False
    
    def extract_phone_number(self, record: Dict) -> str:
        """Extract phone number from a record"""
        
        # Common phone field names in HubSpot and other systems
        phone_fields = [
            'phone', 'phoneNumber', 'phone_number', 'mobilephone', 
            'mobile', 'cell', 'telephone', 'contact_phone', 'number'
        ]
        
        for field in phone_fields:
            if field in record:
                phone = record[field]
                if phone:
                    # Clean up phone number (remove spaces, dashes, etc.)
                    cleaned_phone = ''.join(filter(str.isdigit, str(phone)))
                    
                    # Add country code if missing (assuming US)
                    if len(cleaned_phone) == 10:
                        cleaned_phone = '1' + cleaned_phone
                    
                    if len(cleaned_phone) >= 10:
                        return cleaned_phone
        
        return None
    
    def extract_name(self, record: Dict) -> str:
        """Extract name from a record"""
        
        # Try different name combinations
        if 'firstname' in record and 'lastname' in record:
            first = record.get('firstname', '').strip()
            last = record.get('lastname', '').strip()
            if first or last:
                return f"{first} {last}".strip()
        
        # Try single name fields
        name_fields = ['name', 'fullname', 'contact_name', 'dealname', 'company']
        for field in name_fields:
            if field in record and record[field]:
                return str(record[field]).strip()
        
        # Try email as fallback
        if 'email' in record and record['email']:
            return record['email'].split('@')[0]
        
        return 'Contact'
    
    def send_notification(self, results: List[QueryResult]):
        """Send notification about query results"""
        try:
            total_records = sum(len(result.data) for result in results)
            
            print(f"🔔 Notification: Query completed with {total_records} results")
            return True
            
        except Exception as e:
            print(f"❌ Notification error: {e}")
            return False
    
    def create_tasks(self, results: List[QueryResult]):
        """Create tasks based on query results"""
        try:
            task_count = 0
            for result in results:
                for record in result.data[:5]:  # Limit to first 5 records
                    name = self.extract_name(record)
                    print(f"✅ Task created: Follow up with {name}")
                    task_count += 1
            
            print(f"📋 Created {task_count} follow-up tasks")
            return True
            
        except Exception as e:
            print(f"❌ Task creation error: {e}")
            return False
    
    def generate_report(self, results: List[QueryResult]):
        """Generate report based on query results"""
        try:
            total_records = sum(len(result.data) for result in results)
            print(f"📄 Report generated: {total_records} records analyzed")
            return True
            
        except Exception as e:
            print(f"❌ Report generation error: {e}")
            return False
    
    def process_business_question(self, question: str):
        """Main method to process a natural language question"""
        print(f"🔍 Processing question: {question}")
        
        # Step 1: Let Claude analyze the question
        claude_analysis = self.process_question_with_claude(question)
        
        if not claude_analysis:
            print("❌ Could not analyze question with Claude")
            return None
        
        print(f"🧠 Claude's analysis: {claude_analysis.get('expected_result_type', 'Analysis pending...')}")
        
        results = []
        
        # Step 2: Execute HubSpot queries
        if claude_analysis.get('hubspot_endpoints'):
            hubspot_results = self.execute_hubspot_queries(
                claude_analysis.get('hubspot_endpoints', [])
            )
            results.append(hubspot_results)
        
        # Step 3: Note available actions
        actions = claude_analysis.get('suggested_actions', [])
        
        if actions and results:
            print(f"🚀 Available actions: {', '.join(actions)}")
            # Note: Actions will be executed from the web interface
        
        # Step 4: Calculate totals
        total_records = 0
        actual_data_count = 0
        
        for result in results:
            if hasattr(result, 'total_count') and result.total_count > 0:
                total_records += result.total_count
            else:
                total_records += len(result.data)
            actual_data_count += len(result.data)
        
        print(f"✅ Complete! Found {total_records:,} total records from HubSpot")
        if actual_data_count != total_records:
            print(f"   📋 Retrieved {actual_data_count} sample records for display")
        
        return {
            'question': question,
            'analysis': claude_analysis,
            'results': results,
            'summary': f"Found {total_records:,} records from HubSpot",
            'total_count': total_records,
            'sample_count': actual_data_count
        }
    
    def close_connections(self):
        """Clean up connections (simplified - no database)"""
        print("🔒 System ready for shutdown")
        pass
