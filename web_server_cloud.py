import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import our cloud system
try:
    from hubspot_claude_cloud import HubSpotClaudeCloud as HubSpotClaudeSystem
except ImportError:
    # Fallback to original if cloud version not available
    from hubspot_claude_system import HubSpotClaudeSystem

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize the HubSpot system
try:
    hubspot_system = HubSpotClaudeSystem()
    print("✅ HubSpot system initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize HubSpot system: {e}")
    hubspot_system = None

@app.route('/')
def index():
    """Serve a simple interface"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>KixieGPT for HubSpot</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .btn:disabled { background: #ccc; cursor: not-allowed; }
            textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .results { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #007bff; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .loading { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 KixieGPT for HubSpot</h1>
            <p>Ask questions about your HubSpot data and get intelligent responses!</p>
            
            <div class="status" id="status">Ready to process questions</div>
            
            <div>
                <h3>Ask a Question</h3>
                <textarea id="question" placeholder="e.g., How many contacts do we have? Show me recent deals over $5000..."></textarea>
                <br>
                <button class="btn" onclick="processQuestion()" id="submitBtn">🚀 Process Question</button>
                <button class="btn" onclick="testConnection()" style="background: #28a745;">🔧 Test Connection</button>
                <button class="btn" onclick="clearResults()" style="background: #6c757d;">🗑️ Clear</button>
            </div>
            
            <div id="results" class="results" style="display:none;">
                <h4>📊 Results</h4>
                <div id="resultsContent"></div>
            </div>
        </div>
        
        <script>
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
                        document.getElementById('resultsContent').innerHTML = `
                            <p><strong>Summary:</strong> ${data.summary}</p>
                            <p><strong>Sample Records:</strong> ${data.results.length}</p>
                            <pre>${JSON.stringify(data.results.slice(0, 3), null, 2)}</pre>
                        `;
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
            
            async function testConnection() {
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
    """Test API connections"""
    try:
        results = {'hubspot': False, 'claude': False, 'errors': []}
        
        if not hubspot_system:
            results['errors'].append('System not initialized')
            return jsonify({'success': False, 'results': results})
        
        # Test HubSpot
        try:
            test_data = hubspot_system.get_hubspot_contacts(limit=1)
            results['hubspot'] = 'total' in test_data
        except Exception as e:
            results['errors'].append(f'HubSpot: {str(e)}')
        
        # Test Claude
        try:
            response = hubspot_system.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}]
            )
            results['claude'] = bool(response.content)
        except Exception as e:
            results['errors'].append(f'Claude: {str(e)}')
        
        success = results['hubspot'] and results['claude']
        return jsonify({'success': success, 'results': results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-question', methods=['POST'])
def process_question():
    """Process a business question"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'error': 'Question required'}), 400
        
        if not hubspot_system:
            return jsonify({'success': False, 'error': 'System not initialized'}), 500
        
        # Process the question
        result = hubspot_system.process_business_question(question)
        
        # Format response
        formatted_results = []
        total_records = 0
        
        if result and 'results' in result:
            for query_result in result['results']:
                total_records += getattr(query_result, 'total_count', len(query_result.data))
                
                for record in query_result.data[:5]:  # Limit for web display
                    formatted_results.append({
                        'source': query_result.source,
                        'data': record
                    })
        
        return jsonify({
            'success': True,
            'question': question,
            'total_records': total_records,
            'results': formatted_results,
            'summary': result.get('summary', 'No summary') if result else 'No results',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    return jsonify({
        'status': 'running',
        'system_initialized': hubspot_system is not None,
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'hubspot_api_key': bool(os.getenv('HUBSPOT_API_KEY')),
            'claude_api_key': bool(os.getenv('ANTHROPIC_API_KEY')),
            'kixie_configured': bool(os.getenv('KIXIE_API_KEY'))
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)