import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class QueryResult:
    """Structure for query results"""
    data: List[Dict]
    source: str  # 'hubspot' or 'combined'
    query_type: str
    timestamp: datetime
    total_count: int = 0

class HubSpotClaudeCloud:
    def __init__(self):
        """Initialize the cloud-ready system"""
        
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
        """Get data from HubSpot API"""
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
    
    def get_hubspot_contacts(self, limit: int = 100, properties: list = None) -> Dict:
        """Get contacts from HubSpot"""
        
        if properties is None:
            properties = ['email', 'firstname', 'lastname', 'phone', 'company', 'createdate']
        
        search_payload = {
            'filterGroups': [],
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
                f"{self.hubspot_base_url}/crm/v3/objects/contacts/search",
                headers=headers,
                json=search_payload
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ HubSpot contacts error: {e}")
            return {}
    
    def process_question_with_claude(self, question: str) -> Dict[str, Any]:
        """Send question to Claude for analysis"""
        
        system_prompt = f"""
        You are an AI assistant that helps analyze business questions about HubSpot CRM data.
        
        Your task is to:
        1. Understand the user's question
        2. Determine what HubSpot data to query
        3. Generate appropriate API calls
        4. Suggest actions based on results
        
        Respond with ONLY a valid JSON object containing:
        - data_sources: ["hubspot"]
        - hubspot_endpoints: [list of endpoint configs]
        - expected_result_type: description
        - suggested_actions: list of actions
        
        Current date: {datetime.now().strftime("%Y-%m-%d")}
        """
        
        try:
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Question: {question}"}
                ]
            )
            
            claude_response = response.content[0].text.strip()
            
            # Try to parse JSON from response
            try:
                return json.loads(claude_response)
            except json.JSONDecodeError:
                # Fallback to simple contact query
                return {
                    "data_sources": ["hubspot"],
                    "hubspot_endpoints": [
                        {
                            "endpoint": "contacts",
                            "params": {"limit": 10, "properties": ["email", "firstname", "lastname"]},
                            "purpose": "Get contact information"
                        }
                    ],
                    "expected_result_type": "Contact records",
                    "suggested_actions": ["send_notification"]
                }
            
        except Exception as e:
            print(f"❌ Claude processing error: {e}")
            return {
                "data_sources": ["hubspot"],
                "hubspot_endpoints": [
                    {
                        "endpoint": "contacts",
                        "params": {"limit": 10},
                        "purpose": "Fallback contact query"
                    }
                ],
                "expected_result_type": "Contact data",
                "suggested_actions": []
            }
    
    def execute_hubspot_queries(self, endpoints: List[Dict]) -> QueryResult:
        """Execute HubSpot API calls"""
        all_data = []
        total_count = 0
        
        for endpoint_config in endpoints:
            endpoint = endpoint_config['endpoint']
            params = endpoint_config.get('params', {})
            
            if 'contacts' in endpoint:
                data = self.get_hubspot_contacts(
                    limit=params.get('limit', 50),
                    properties=params.get('properties', None)
                )
            else:
                data = self.get_hubspot_data(endpoint, params)
            
            if 'results' in data:
                results = data.get('results', [])
                total_count += data.get('total', 0)
                
                # Flatten properties for easier display
                for item in results:
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
    
    def send_kixie_sms(self, target_phone: str, message: str) -> bool:
        """Send SMS via Kixie API"""
        
        url = f"{self.kixie_config['base_url']}?apikey={self.kixie_config['api_key']}&businessid={self.kixie_config['business_id']}"
        
        payload = {
            "businessid": self.kixie_config['business_id'],
            "email": self.kixie_config['sender_email'],
            "target": target_phone,
            "eventname": "sms",
            "message": message,
            "apikey": self.kixie_config['api_key']
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ SMS error: {e}")
            return False
    
    def process_business_question(self, question: str):
        """Main method to process questions"""
        print(f"🔍 Processing: {question}")
        
        # Analyze with Claude
        analysis = self.process_question_with_claude(question)
        
        # Execute HubSpot queries
        results = []
        if analysis.get('hubspot_endpoints'):
            hubspot_results = self.execute_hubspot_queries(analysis['hubspot_endpoints'])
            results.append(hubspot_results)
        
        # Calculate totals
        total_records = sum(getattr(result, 'total_count', len(result.data)) for result in results)
        sample_records = sum(len(result.data) for result in results)
        
        return {
            'question': question,
            'analysis': analysis,
            'results': results,
            'summary': f"Found {total_records:,} total records",
            'total_count': total_records,
            'sample_count': sample_records
        }

# For backwards compatibility
HubSpotClaudeSystem = HubSpotClaudeCloud