import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Import our cloud-compatible system
from hubspot_claude_system_cloud import HubSpotClaudeSystem

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
        # Try to read your existing HTML file first
        with open('web_interface.html', 'r') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        # Fallback to a simple interface if the file doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>KixieGPT for HubSpot</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
                h1 { color: #333; text-align: center; margin-bottom: 10px; }
                .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
                .btn { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 14px 28px; border: none; border-radius: 8px; cursor: pointer; margin: 8px; font-size: 16px; transition: transform 0.2s; }
                .btn:hover { transform: translateY(-2px); }
                .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
                .btn-test { background: linear-gradient(135deg, #28a745, #20c997); }
                .btn-clear { background: linear-gradient(135deg, #6c757d, #495057); }
                textarea { width: 100%; height: 120px; margin: 15px 0; padding: 15px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 16px; resize: vertical; }
                textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
                .results { background: #f8f9fa; padding: 25px; margin: 25px 0; border-radius: 8px; border-left: 4px solid #667eea; }
                .status { padding: 15px; margin: 15px 0; border-radius: 8px; font-weight: 500; }
                .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
                .examples { background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .example { background: white; padding: 10px; margin: 8px 0; border-radius: 5px; cursor: pointer; border: 1px solid #ddd; transition: border-color 0.2s; }
                .example:hover { border-color: #667eea; }
                pre { background: #2d3748; color: #e2e8f0; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 14px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 KixieGPT for HubSpot</h1>
                <p class="subtitle">Ask intelligent questions about your HubSpot data</p>
                
                <div class="status" id="status">Ready to process questions</div>
                
                <div class="examples">
                    <h3>💡 Example Questions</h3>
                    <div class="example" onclick="setQuestion('How many contacts do we have total?')">
                        📊 How many contacts do we have total?
                    </div>
                    <div class="example" onclick="setQuestion('Show me our 5 most recent contacts')">
                        👥 Show me our 5 most recent contacts
                    </div>
                    <div class="example" onclick="setQuestion('Find contacts that contain phone number 14244854061')">
                        📞 Find contacts that contain phone number 14244854061
                    </div>
                </div>
                
                <div>
                    <h3>Ask Your Question</h3>
                    <textarea id="question" placeholder="e.g., How many contacts were created this month? Show me deals over $10,000..."></textarea>
                    <br>
                    <button class="btn" onclick="processQuestion()" id="submitBtn">🚀 Process Question</button>
                    <button class="btn btn-test" onclick="testConnections()">🔧 Test Connections</button>
                    <button class="btn btn-clear" onclick="clearResults()">🗑️ Clear</button>
                </div>
                
                <div id="results" class="results" style="display:none;">
                    <h4>📊 Results</h4>
                    <div id="resultsContent"></div>
                </div>
            </div>
            
            <script>
                function setQuestion(q) {
                    document.getElementById('question').value = q;
                }
                
                async function processQuestion() {
                    const question = document.getElementById('question').value.trim();
                    const statusDiv = document.getElementById('status');
                    const resultsDiv = document.getElementById('results');
                    const submitBtn = document.getElementById('submitBtn');
                    
                    if (!question) {
                        alert('Please enter a question');
                        return;
                    }
                    
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Processing...';
                    statusDiv.className = 'status loading';
                    statusDiv.textContent = 'Processing your question...';
                    
                    try {
                        const response = await fetch('/api/process-question', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ question: question })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            statusDiv.className = 'status success';
                            statusDiv.textContent = `✅ Found ${data.total_records} records!`;
                            
                            resultsDiv.style.display = 'block';
                            let html = `<p><strong>Summary:</strong> ${data.summary}</p>`;
                            
                            if (data.results && data.results.length > 0) {
                                html += `<h5>Sample Results (${data.results.length} shown):</h5>`;
                                html += '<pre>' + JSON.stringify(data.results.slice(0, 3), null, 2) + '</pre>';
                            }
                            
                            document.getElementById('resultsContent').innerHTML = html;
                        } else {
                            statusDiv.className = 'status error';
                            statusDiv.textContent = `❌ Error: ${data.error}`;
                            resultsDiv.style.display = 'none';
                        }
                    } catch (error) {
                        statusDiv.className = 'status error';
                        statusDiv.textContent = `❌ Network error: ${error.message}`;
                        resultsDiv.style.display = 'none';
                    }
                    
                    submitBtn.disabled = false;
                    submitBtn.textContent = '🚀 Process Question';
                }
                
                async function testConnections() {
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = 'status loading';
                    statusDiv.textContent = 'Testing connections...';
                    
                    try {
                        const response = await fetch('/api/test-connections', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            statusDiv.className = 'status success';
                            statusDiv.textContent = '✅ All connections working!';
                        } else {
                            statusDiv.className = 'status error';
                            statusDiv.textContent = `❌ Connection issues: ${data.error}`;
                        }
                    } catch (error) {
                        statusDiv.className = 'status error';
                        statusDiv.textContent = `❌ Test failed: ${error.message}`;
                    }
                }
                
                function clearResults() {
                    document.getElementById('results').style.display = 'none';
                    document.getElementById('status').className = 'status';
                    document.getElementById('status').textContent = 'Ready to process questions';
                }
                
                // Allow Enter key to submit
                document.getElementById('question').addEventListener('keydown', function(e) {
                    if (e.ctrlKey && e.key === 'Enter') {
                        processQuestion();
                    }
                });
            </script>
        </body>
        </html>
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
        
        # Test MySQL connection (will return False in cloud mode, which is expected)
        try:
            mysql_connected = hubspot_system.connect_to_database()
            results['mysql'] = mysql_connected
            if not mysql_connected:
                results['errors'].append('MySQL: Not available in cloud mode (this is normal)')
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
                results['errors'].append('Kixie: Missing API credentials (optional)')
        except Exception as e:
            results['errors'].append(f'Kixie: {str(e)}')
        
        # Consider success if HubSpot and Claude work (MySQL is optional in cloud)
        success = results['hubspot'] and results['claude']
        
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
        from hubspot_claude_system_cloud import QueryResult
        
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

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy'}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting HubSpot Query Web Interface Server (Cloud Mode)")
    print("=" * 50)
    
    # Check environment
    required_vars = ['HUBSPOT_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠️  Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("Some features may not work properly.")
    else:
        print("✅ All required environment variables found")
    
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🌐 Server starting at: http://0.0.0.0:{port}")
    print("📱 API endpoints available")
    print("☁️  Running in cloud mode (MySQL disabled)")
    
    # Start the Flask server
    app.run(debug=False, host='0.0.0.0', port=port)