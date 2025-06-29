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
        except requests.exceptions.RequestException as e:
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
        except requests.exceptions.RequestException as e:
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
        HubSpot stores phone numbers in different formats, so we need to try different approaches.
        
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
        
        IMPORTANT DATE HANDLING:
        For date-based queries, use these EXACT date values (do NOT use template syntax):
        
        **"This month" queries:**
        "filterGroups": [
            {{
                "filters": [
                    {{
                        "operator": "GTE",
                        "propertyName": "createdate",
                        "value": "{current_month_start_iso}"
                    }}
                ]
            }}
        ]
        
        **"Last month" queries:**
        "filterGroups": [
            {{
                "filters": [
                    {{
                        "operator": "GTE",
                        "propertyName": "createdate",
                        "value": "{last_month_start_iso}"
                    }},
                    {{
                        "operator": "LT",
                        "propertyName": "createdate", 
                        "value": "{current_month_start_iso}"
                    }}
                ]
            }}
        ]
        
        **"This week" queries:**
        "filterGroups": [
            {{
                "filters": [
                    {{
                        "operator": "GTE",
                        "propertyName": "createdate",
                        "value": "{week_start_iso}"
                    }}
                ]
            }}
        ]
        
        CRITICAL: Always set limit to 1 for "only 1" or "find 1" requests.
        The system will automatically stop after finding the first successful result.
        
        For NON-PHONE searches, use standard operators:
        - EQ for exact matches (email, ID)
        - CONTAINS_TOKEN for partial matches (names, text)
        
        IMPORTANT: Respond with ONLY a valid JSON object, no additional text.
        
        Example for "Find only 1 contact that contains the phone number 14244854061":
        {{
            "data_sources": ["hubspot"],
            "hubspot_endpoints": [
                {{
                    "endpoint": "contacts", 
                    "params": {{
                        "limit": 1, 
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
                        "limit": 1, 
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
                        "limit": 1, 
                        "properties": ["email", "firstname", "lastname", "phone", "hs_searchable_calculated_phone_number"],
                        "query": "4244854061"
                    }}, 
                    "purpose": "Strategy 3: General search query"
                }}
            ],
            "expected_result_type": "Single contact record with matching phone number",
            "suggested_actions": ["send_sms", "create_task"],
            "action_triggers": {{"when_single_match_found": "send_sms"}}
        }}
        
        Common HubSpot endpoints:
        - "contacts" for contact data
        - "deals" for deal/opportunity data  
        - "companies" for company/account data
        - "tickets" for support ticket data
        
        Available actions:
        - "send_sms" - Send SMS via Kixie to contacts with phone numbers
        - "create_task" - Create follow-up tasks
        - "send_notification" - Send team notifications
        - "generate_report" - Generate summary reports
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
        
        from datetime import datetime, timedelta
        
        # Get current date information
        now = datetime.now()
        current_month_start = datetime(now.year, now.month, 1)
        current_month_start_iso = current_month_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        question_lower = question.lower()
        
        # Check for date-based queries first
        if any(word in question_lower for word in ['this month', 'current month', 'month']):
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "contacts", 
                        "params": {
                            "limit": 100, 
                            "properties": ["email", "firstname", "lastname", "createdate"],
                            "filterGroups": [
                                {
                                    "filters": [
                                        {
                                            "operator": "GTE",
                                            "propertyName": "createdate",
                                            "value": current_month_start_iso
                                        }
                                    ]
                                }
                            ]
                        }, 
                        "purpose": "Get contacts created this month (fallback)"
                    }
                ],
                "expected_result_type": "Contacts created this month",
                "suggested_actions": ["generate_report"],
                "action_triggers": {}
            }
        
        # Check for other query types
        elif any(word in question_lower for word in ['contact', 'people', 'customer', 'lead']):
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
        found_actual_results = False
        unique_contacts = {}  # Track unique contacts to avoid duplicates
        
        # Check if this is a specific search (limit <= 5) 
        is_specific_search = any(
            endpoint_config.get('params', {}).get('limit', 50) <= 5 
            for endpoint_config in endpoints
        )
        
        # Check if this appears to be a multi-item search (multiple phone numbers, emails, etc.)
        is_multi_item_search = self.detect_multi_item_search(endpoints)
        
        print(f"🔍 Executing {'multi-item' if is_multi_item_search else 'specific' if is_specific_search else 'general'} search with {len(endpoints)} strategies")
        
        for i, endpoint_config in enumerate(endpoints):
            # For single-item specific searches, stop after finding results
            # For multi-item searches, continue until all strategies are tried
            if is_specific_search and not is_multi_item_search and found_actual_results:
                print(f"⏭️  Skipping strategy {i+1} - already found results for single-item search")
                break
                
            endpoint = endpoint_config['endpoint']
            params = endpoint_config.get('params', {})
            purpose = endpoint_config.get('purpose', f'Strategy {i+1}')
            
            print(f"📡 Trying {purpose}")
            print(f"🔍 Query params: {params}")
            
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
                
                # If we found actual contact records (not just counts)
                if results_count > 0:
                    print(f"   ✅ SUCCESS: {purpose} found {results_count} actual contact(s)!")
                    found_actual_results = True
                    total_count += api_total
                    
                    # Extract and flatten properties, avoiding duplicates
                    for item in actual_results:
                        contact_id = item.get('id')
                        
                        # Skip if we already have this contact
                        if contact_id and contact_id in unique_contacts:
                            print(f"   🔄 Skipping duplicate contact ID: {contact_id}")
                            continue
                        
                        if 'properties' in item:
                            flattened = {'id': item.get('id')}
                            flattened.update(item['properties'])
                            
                            # Mark this contact as found
                            if contact_id:
                                unique_contacts[contact_id] = True
                            
                            all_data.append(flattened)
                        else:
                            all_data.append(item)
                    
                    print(f"   📋 Added {len(actual_results)} new contacts (total unique: {len(all_data)})")
                    
                else:
                    print(f"   ⚠️  {purpose} found {api_total} total records but 0 actual results")
                    
                    # Only add count records if we haven't found actual results yet
                    if not found_actual_results and api_total > 0:
                        summary_record = {
                            'query_type': 'count',
                            'total_count': api_total,
                            'endpoint': endpoint,
                            'purpose': purpose,
                            'summary': f"Total {endpoint}: {api_total:,} records available"
                        }
                        all_data.append(summary_record)
                        total_count += api_total
            
            elif data:
                print(f"   ℹ️  {purpose} returned other data")
                all_data.append(data)
        
        # Final result summary
        actual_contacts = [item for item in all_data if 'query_type' not in item]
        print(f"📋 Final results: {len(actual_contacts)} unique contacts, {len(all_data)} total records")
        
        return QueryResult(
            data=all_data,
            source='hubspot',
            query_type='api_call',
            timestamp=datetime.now(),
            total_count=total_count
        )
    
    def detect_multi_item_search(self, endpoints: List[Dict]) -> bool:
        """Detect if this is a search for multiple specific items"""
        
        # Look for different search values across strategies
        search_values = set()
        phone_numbers = set()
        
        for endpoint_config in endpoints:
            params = endpoint_config.get('params', {})
            
            # Check query parameter
            query = params.get('query')
            if query:
                search_values.add(query.strip())
            
            # Check filter values
            filter_groups = params.get('filterGroups', [])
            for group in filter_groups:
                for filter_item in group.get('filters', []):
                    value = filter_item.get('value', '').strip()
                    if value:
                        search_values.add(value)
                        
                        # If it looks like a phone number, track it separately
                        if value.isdigit() and len(value) >= 10:
                            # Normalize phone number (remove country code variations)
                            normalized = value.lstrip('1') if value.startswith('1') and len(value) == 11 else value
                            phone_numbers.add(normalized)
        
        # If we have multiple distinct search values or phone numbers, it's a multi-item search
        is_multi = len(search_values) > 2 or len(phone_numbers) > 1
        
        if is_multi:
            print(f"🔢 Detected multi-item search: {len(search_values)} search values, {len(phone_numbers)} phone numbers")
            print(f"   📞 Phone numbers: {list(phone_numbers)}")
        
        return is_multi
    
    def get_contact_deals(self, contact_id: str) -> List[Dict]:
        """Get deals associated with a specific contact"""
        try:
            # HubSpot API call to get deals for a contact
            url = f"{self.hubspot_base_url}/crm/v4/objects/contacts/{contact_id}/associations/deals"
            headers = {
                'Authorization': f'Bearer {self.hubspot_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            associations_data = response.json()
            
            if not associations_data.get('results'):
                return []
            
            # Get deal IDs
            deal_ids = [item['toObjectId'] for item in associations_data['results']]
            
            if not deal_ids:
                return []
            
            # Fetch deal details in batch
            deals_data = self.get_deals_by_ids(deal_ids)
            return deals_data
            
        except Exception as e:
            print(f"❌ Error fetching deals for contact {contact_id}: {e}")
            return []
    
    def get_deals_by_ids(self, deal_ids: List[str]) -> List[Dict]:
        """Get detailed information for specific deal IDs"""
        try:
            deals = []
            # Process in batches of 10 (HubSpot limit)
            batch_size = 10
            
            for i in range(0, len(deal_ids), batch_size):
                batch_ids = deal_ids[i:i + batch_size]
                
                search_payload = {
                    'filterGroups': [
                        {
                            'filters': [
                                {
                                    'propertyName': 'hs_object_id',
                                    'operator': 'IN',
                                    'values': batch_ids
                                }
                            ]
                        }
                    ],
                    'properties': [
                        'dealname', 'amount', 'dealstage', 'pipeline', 
                        'closedate', 'createdate', 'hubspot_owner_id', 'dealtype'
                    ],
                    'limit': batch_size
                }
                
                headers = {
                    'Authorization': f'Bearer {self.hubspot_api_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    f"{self.hubspot_base_url}/crm/v3/objects/deals/search",
                    headers=headers,
                    json=search_payload
                )
                response.raise_for_status()
                
                batch_data = response.json()
                if batch_data.get('results'):
                    for deal in batch_data['results']:
                        if 'properties' in deal:
                            # Flatten properties
                            flattened = {'id': deal.get('id')}
                            flattened.update(deal['properties'])
                            deals.append(flattened)
            
            return deals
            
        except Exception as e:
            print(f"❌ Error fetching deal details: {e}")
            return []
    
    def create_enhanced_sms_message(self, contact_record: Dict, deals: List[Dict]) -> str:
        """Create a personalized SMS message including deal information"""
        
        # Extract contact information
        name = self.extract_name(contact_record)
        
        # Base greeting
        if deals:
            # Contact has deals - create personalized message
            return self.create_sms_with_deals(name, deals, contact_record)
        else:
            # Contact has no deals - create general follow-up message
            return self.create_sms_without_deals(name, contact_record)
    
    def create_sms_with_deals(self, name: str, deals: List[Dict], contact_record: Dict) -> str:
        """Create SMS message when contact has deal data"""
        
        # Sort deals by amount (highest first) and recency
        sorted_deals = sorted(deals, key=lambda d: (
            self.parse_deal_amount(d.get('amount', '0')), 
            d.get('createdate', '')
        ), reverse=True)
        
        # Focus on the most significant deal(s)
        primary_deal = sorted_deals[0] if sorted_deals else None
        
        if not primary_deal:
            return self.create_sms_without_deals(name, contact_record)
        
        deal_name = primary_deal.get('dealname', 'your opportunity')
        deal_amount = self.format_deal_amount(primary_deal.get('amount'))
        deal_stage = primary_deal.get('dealstage', 'in progress')
        
        # Create different messages based on deal stage and amount
        if 'closed' in deal_stage.lower() and 'won' in deal_stage.lower():
            # Closed won deal
            message = f"Hi {name}! Congratulations on closing {deal_name}"
            if deal_amount:
                message += f" for {deal_amount}"
            message += "! How are things going? Let's discuss next steps."
            
        elif 'closed' in deal_stage.lower() and 'lost' in deal_stage.lower():
            # Closed lost deal
            message = f"Hi {name}, I wanted to follow up on {deal_name}. I'd love to understand what we could improve for future opportunities. Are you available for a quick chat?"
            
        elif any(stage in deal_stage.lower() for stage in ['proposal', 'quote', 'contract']):
            # Deal in proposal/contract stage
            message = f"Hi {name}! Checking in on {deal_name}"
            if deal_amount:
                message += f" ({deal_amount})"
            message += ". Do you have any questions about the proposal? Happy to discuss!"
            
        elif any(stage in deal_stage.lower() for stage in ['negotiation', 'decision']):
            # Deal in negotiation/decision stage
            message = f"Hi {name}, following up on {deal_name}"
            if deal_amount:
                message += f" ({deal_amount})"
            message += ". I'm here to help with any final questions or concerns you might have."
            
        else:
            # Early stage or unknown stage
            message = f"Hi {name}! Wanted to touch base about {deal_name}"
            if deal_amount:
                message += f" ({deal_amount})"
            message += ". How can I best support you moving forward?"
        
        # Add multiple deals context if applicable
        if len(sorted_deals) > 1:
            message += f" (+ {len(sorted_deals) - 1} other opportunities)"
        
        # Keep message under 160 characters for single SMS if possible
        if len(message) > 160:
            # Create shorter version
            message = f"Hi {name}! Following up on {deal_name}"
            if deal_amount:
                message += f" ({deal_amount})"
            message += ". Let's connect soon!"
        
        return message
    
    def create_sms_without_deals(self, name: str, contact_record: Dict) -> str:
        """Create SMS message when contact has no deal data"""
        
        # Check when contact was created to personalize message
        created_date = contact_record.get('createdate', '')
        company = contact_record.get('company', '')
        
        if company:
            message = f"Hi {name}! Hope things are going well at {company}. I'd love to explore how we can help support your goals. Are you available for a brief call?"
        else:
            message = f"Hi {name}! I wanted to reach out and see how we might be able to help with your current projects. Would you be interested in a quick conversation?"
        
        # Keep under 160 characters
        if len(message) > 160:
            if company:
                message = f"Hi {name}! Hope all is well at {company}. Would love to connect about how we can help. Available for a quick call?"
            else:
                message = f"Hi {name}! Would love to connect about your current projects and how we might help. Available for a quick call?"
        
        return message
    
    def parse_deal_amount(self, amount_str: str) -> float:
        """Parse deal amount string to float for sorting"""
        if not amount_str:
            return 0.0
        
        # Remove currency symbols, commas, and spaces
        clean_amount = ''.join(c for c in str(amount_str) if c.isdigit() or c == '.')
        
        try:
            return float(clean_amount) if clean_amount else 0.0
        except ValueError:
            return 0.0
    
    def format_deal_amount(self, amount_str: str) -> str:
        """Format deal amount for display in SMS"""
        if not amount_str:
            return ""
        
        amount = self.parse_deal_amount(amount_str)
        if amount <= 0:
            return ""
        
        # Format based on amount size
        if amount >= 1000000:
            return f"${amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"${amount/1000:.0f}K"
        else:
            return f"${amount:.0f}"
    
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
        """Send SMS notifications via Kixie API based on query results (Enhanced with Deal Data)"""
        try:
            print("📱 Sending enhanced SMS notifications via Kixie...")
            
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
                    contact_id = record.get('id')
                    
                    print(f"📞 Processing contact: {name} (ID: {contact_id})")
                    
                    # Fetch deal data for this contact
                    deals = []
                    if contact_id:
                        print(f"🔍 Fetching deals for contact {contact_id}...")
                        deals = self.get_contact_deals(contact_id)
                        print(f"💼 Found {len(deals)} deals for {name}")
                        
                        # Log deal details for debugging
                        for deal in deals:
                            deal_name = deal.get('dealname', 'Unknown')
                            deal_amount = deal.get('amount', 'Unknown')
                            deal_stage = deal.get('dealstage', 'Unknown')
                            print(f"   📋 Deal: {deal_name} | ${deal_amount} | {deal_stage}")
                    
                    # Create enhanced personalized message
                    message = self.create_enhanced_sms_message(record, deals)
                    
                    print(f"💬 Message for {name}: {message}")
                    
                    # Send SMS via Kixie
                    success = self.send_single_kixie_sms(
                        target_phone=phone,
                        message=message,
                        sender_email=self.kixie_config['sender_email']
                    )
                    
                    if success:
                        sms_count += 1
                        deals_info = f" (with {len(deals)} deals)" if deals else " (no deals)"
                        print(f"✅ Enhanced SMS sent to {name} ({phone}){deals_info}")
                    else:
                        print(f"❌ Failed to send SMS to {name} ({phone})")
            
            print(f"📊 Enhanced SMS Summary: {sms_count} personalized messages sent successfully")
            return sms_count > 0
            
        except Exception as e:
            print(f"❌ Enhanced SMS campaign error: {e}")
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
        
        # Step 4: Calculate totals - use API total_count when available
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

# Example usage and test scenarios
if __name__ == "__main__":
    # Initialize the system
    system = HubSpotClaudeSystem()
    
    # Example business questions you can ask
    example_questions = [
        "How many contacts do we have?",
        "Show me recent contacts",
        "Find contacts from California",
        "Show me contacts in the technology industry",
        "Find contacts created this week",
        "Show me deals over $5,000",
        "Which companies have the most contacts?"
    ]
    
    try:
        # Process a sample question
        sample_question = "How many contacts do we have?"
        result = system.process_business_question(sample_question)
        
        if result:
            print("\n" + "="*60)
            print("RESULT SUMMARY:")
            print("="*60)
            print(f"Question: {result['question']}")
            print(f"Summary: {result['summary']}")
        else:
            print("❌ No result returned")
        
    except Exception as e:
        print(f"❌ Error processing question: {e}")
    
    finally:
        system.close_connections()