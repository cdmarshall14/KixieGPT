import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Import our main system
from hubspot_claude_system import HubSpotClaudeSystem

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

# Initialize the HubSpot system
try:
    hubspot_system = HubSpotClaudeSystem()
    print("✅ HubSpot system initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize HubSpot system: {e}")
    hubspot_system = None

@app.route('/')
def index():
    """Serve the main web interface"""
    try:
        # Read the HTML file we created
        with open('web_interface.html', 'r') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return '''
        <h1>HubSpot Query Interface</h1>
        <p>Please make sure the web_interface.html file is in the same directory as this server.</p>
        <p>You can copy the HTML content from the artifact and save it as "web_interface.html"</p>
        '''

@app.route('/api/test-connections', methods=['POST'])
def test_connections():
    """Test all API connections"""
    
    try:
        results = {
            'hubspot': False,
            'claude': False,
            'mysql': False,
            'kixie': False,
            'errors': []
        }
        
        if not hubspot_system:
            results['errors'].append('HubSpot system not initialized')
            return jsonify({'success': False, 'results': results})
        
        # Test HubSpot connection
        try:
            # Test with a simple API call
            test_data = hubspot_system.get_hubspot_data('crm/v3/objects/contacts', {'limit': 1})
            results['hubspot'] = 'total' in test_data or 'results' in test_data
        except Exception as e:
            results['errors'].append(f'HubSpot: {str(e)}')
        
        # Test MySQL connection
        try:
            if hubspot_system.connect_to_database():
                results['mysql'] = True
            else:
                results['errors'].append('MySQL: Connection failed')
        except Exception as e:
            results['errors'].append(f'MySQL: {str(e)}')
        
        # Test Claude API
        try:
            response = hubspot_system.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            results['claude'] = bool(response.content)
        except Exception as e:
            results['errors'].append(f'Claude: {str(e)}')
        
        # Test Kixie SMS API
        try:
            # Just validate configuration, don't send actual SMS
            if hubspot_system.kixie_config['api_key'] and hubspot_system.kixie_config['business_id']:
                results['kixie'] = True
            else:
                results['errors'].append('Kixie: Missing API credentials')
        except Exception as e:
            results['errors'].append(f'Kixie: {str(e)}')
        
        success = all([results['hubspot'], results['claude'], results['mysql'], results['kixie']])
        
        return jsonify({
            'success': success,
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/process-question', methods=['POST'])
def process_question():
    """Process a business question using the HubSpot system"""
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        action_type = data.get('action_type', '')
        
        if not question:
            return jsonify({'success': False, 'error': 'Question is required'}), 400
        
        if not hubspot_system:
            return jsonify({'success': False, 'error': 'HubSpot system not initialized'}), 500
        
        # Process the question
        result = hubspot_system.process_business_question(question)
        
        # Format the response for the web interface
        formatted_results = []
        total_records = 0
        
        if result and 'results' in result:
            for query_result in result['results']:
                total_records += len(query_result.data)
                
                # Format each record for display
                for record in query_result.data[:10]:  # Limit to first 10 for web display
                    formatted_record = {
                        'source': query_result.source,
                        'data': record
                    }
                    formatted_results.append(formatted_record)
        
        response = {
            'success': True,
            'question': question,
            'total_records': total_records,
            'results': formatted_results,
            'analysis': result.get('analysis', {}) if result else {},
            'summary': result.get('summary', 'No summary available') if result else 'No results',
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/execute-action', methods=['POST'])
def execute_action():
    """Execute an action on the last query results"""
    
    try:
        data = request.get_json()
        action_type = data.get('action_type', '')
        results_data = data.get('results', [])
        
        if not action_type:
            return jsonify({'success': False, 'error': 'Action type is required'}), 400
        
        if not hubspot_system:
            return jsonify({'success': False, 'error': 'HubSpot system not initialized'}), 500
        
        # Convert web results back to QueryResult objects for processing
        from hubspot_claude_system import QueryResult
        
        query_results = []
        
        # Group results by source
        sources = {}
        for item in results_data:
            source = item.get('source', 'unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(item.get('data', {}))
        
        # Create QueryResult objects
        for source, data_list in sources.items():
            query_result = QueryResult(
                data=data_list,
                source=source,
                query_type='web_interface',
                timestamp=datetime.now()
            )
            query_results.append(query_result)
        
        # Execute the action
        hubspot_system.execute_external_actions(
            results=query_results,
            actions=[action_type],
            triggers={}
        )
        
        return jsonify({
            'success': True,
            'action': action_type,
            'processed_records': sum(len(qr.data) for qr in query_results),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/send-test-sms', methods=['POST'])
def send_test_sms():
    """Send a test SMS"""
    
    try:
        data = request.get_json()
        phone = data.get('phone', os.getenv('TEST_PHONE_NUMBER'))
        message = data.get('message', f'Test SMS from HubSpot interface at {datetime.now().strftime("%H:%M:%S")}')
        
        if not phone:
            return jsonify({'success': False, 'error': 'Phone number is required'}), 400
        
        if not hubspot_system:
            return jsonify({'success': False, 'error': 'HubSpot system not initialized'}), 500
        
        # Send the SMS
        success = hubspot_system.send_single_kixie_sms(
            target_phone=phone,
            message=message
        )
        
        return jsonify({
            'success': success,
            'phone': phone,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    
    status = {
        'system_initialized': hubspot_system is not None,
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'hubspot_api_key': bool(os.getenv('HUBSPOT_API_KEY')),
            'claude_api_key': bool(os.getenv('ANTHROPIC_API_KEY')),
            'mysql_configured': bool(os.getenv('MYSQL_HOST')),
            'kixie_configured': bool(os.getenv('KIXIE_API_KEY'))
        }
    }
    
    return jsonify(status)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def create_html_file():
    """Create the HTML file if it doesn't exist"""
    
    if not os.path.exists('web_interface.html'):
        print("Creating web_interface.html file...")
        
        # This is a simplified version - you should copy the full HTML from the artifact
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>HubSpot Query Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        textarea { width: 100%; height: 100px; margin: 10px 0; }
        .results { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>HubSpot + Claude Query Interface</h1>
        <p>Please copy the full HTML content from the web_interface artifact to replace this file.</p>
        <p>This is just a placeholder. The full interface has many more features!</p>
        
        <div>
            <h3>Quick Test</h3>
            <textarea id="question" placeholder="Enter your question here..."></textarea>
            <button class="btn" onclick="testQuery()">Test Query</button>
            <div id="results" class="results" style="display:none;"></div>
        </div>
    </div>
    
    <script>
        async function testQuery() {
            const question = document.getElementById('question').value;
            const resultsDiv = document.getElementById('results');
            
            if (!question.trim()) {
                alert('Please enter a question');
                return;
            }
            
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = 'Processing...';
            
            try {
                const response = await fetch('/api/process-question', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    resultsDiv.innerHTML = `
                        <h4>Results: ${data.total_records} records found</h4>
                        <p><strong>Summary:</strong> ${data.summary}</p>
                        <pre>${JSON.stringify(data.results.slice(0, 3), null, 2)}</pre>
                    `;
                } else {
                    resultsDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
                }
            } catch (error) {
                resultsDiv.innerHTML = `<p style="color:red;">Network error: ${error.message}</p>`;
            }
        }
    </script>
</body>
</html>'''
        
        with open('web_interface.html', 'w') as f:
            f.write(html_content)
        
        print("✅ web_interface.html created")
        print("💡 For the full interface, copy the HTML content from the 'Complete HubSpot Query Web Interface' artifact")

if __name__ == '__main__':
    print("🚀 Starting HubSpot Query Web Interface Server")
    print("=" * 50)
    
    # Create HTML file if needed
    create_html_file()
    
    # Check environment
    required_vars = ['HUBSPOT_API_KEY', 'ANTHROPIC_API_KEY', 'MYSQL_HOST']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("Some features may not work properly.")
    
    print(f"\n🌐 Server starting at: http://localhost:5000")
    print("📱 API endpoints available at: http://localhost:5000/api/")
    print("\nPress Ctrl+C to stop the server")
    
    # Start the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)