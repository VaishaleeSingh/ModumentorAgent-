#!/usr/bin/env python3
"""
Standalone Agentic Server for ModuMentor
Deploy this separately from the Node.js server
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

try:
    from agents.intelligent_agent import IntelligentAgent
    from config import config
    print("✅ Successfully imported intelligent agent modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Global agent instance
agent = None

def initialize_agent():
    """Initialize the intelligent agent"""
    global agent
    try:
        agent = IntelligentAgent()
        logger.info(f"✅ Intelligent agent initialized successfully with ID: {id(agent)}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        agent = None
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'agent_initialized': agent is not None,
        'service': 'modumentor-agentic-server'
    })

@app.route('/api/chat', methods=['POST'])
def process_message():
    """Process a message through the intelligent agent"""
    global agent
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'web-user')
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Initialize agent if needed
        if not agent:
            if not initialize_agent():
                return jsonify({
                    'error': 'Failed to initialize intelligent agent',
                    'response': 'I\'m sorry, but I\'m having trouble connecting to my AI brain right now. Please try again later.'
                }), 500
        
        logger.info(f"Processing message: '{message}' for user {user_id}")
        
        # Create event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response = loop.run_until_complete(
                agent.process_message(message, user_id)
            )
            
            logger.info(f"Agent response generated successfully")
            
            return jsonify({
                'response': response,
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return jsonify({
            'error': str(e),
            'response': f'I encountered an error while processing your message: {str(e)}',
            'success': False
        }), 500

@app.route('/api/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation history for a user"""
    global agent
    
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'web-user') if data else 'web-user'
        
        if not agent:
            if not initialize_agent():
                return jsonify({
                    'error': 'Failed to initialize intelligent agent',
                    'success': False
                }), 500
        
        # Clear conversation memory
        agent.conversation_memory.clear_conversation(user_id)
        
        logger.info(f"Cleared conversation for user: {user_id}")
        
        return jsonify({
            'success': True,
            'response': 'Conversation cleared successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/help', methods=['GET'])
def get_help():
    """Get help information"""
    global agent
    
    try:
        if not agent:
            if not initialize_agent():
                return jsonify({
                    'error': 'Failed to initialize intelligent agent',
                    'success': False
                }), 500
        
        # Create event loop for async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            help_message = loop.run_until_complete(agent.get_help_message())
            
            return jsonify({
                'success': True,
                'response': help_message,
                'timestamp': datetime.now().isoformat()
            })
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error getting help: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_conversation():
    """Analyze conversation for a user"""
    global agent
    
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'web-user') if data else 'web-user'
        
        if not agent:
            if not initialize_agent():
                return jsonify({
                    'error': 'Failed to initialize intelligent agent',
                    'success': False
                }), 500
        
        # Get conversation analysis
        analysis = agent.conversation_memory.analyze_conversation(user_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error analyzing conversation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/tools', methods=['GET'])
def get_available_tools():
    """Get list of available tools"""
    global agent
    
    try:
        if not agent:
            if not initialize_agent():
                return jsonify({
                    'error': 'Failed to initialize intelligent agent',
                    'success': False
                }), 500
        
        tools = agent.tool_manager.get_available_tools()
        
        return jsonify({
            'success': True,
            'tools': tools,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting tools: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

if __name__ == '__main__':
    # Initialize agent on startup
    logger.info("🚀 Starting ModuMentor Agentic Server...")
    
    if initialize_agent():
        logger.info("✅ Agent initialized successfully")
    else:
        logger.warning("⚠️ Agent initialization failed, will initialize on first request")
    
    # Get port from environment or use default
    port = int(os.getenv('AGENTIC_PORT', 5001))
    host = os.getenv('AGENTIC_HOST', '0.0.0.0')
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    app.run(host=host, port=port, debug=False) 