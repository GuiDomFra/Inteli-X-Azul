#!/usr/bin/env python3
"""Run Flask app with mocked Anthropic client (no API key needed)."""
import os
from unittest.mock import MagicMock

# Must set before importing brand_advisor
mock_client = MagicMock()
mock_response = MagicMock()
mock_response.stop_reason = 'end_turn'
mock_response.model = 'claude-opus-4-8-mock'
mock_response.content = [MagicMock(type='text', text='{"semaforo": "verde", "riscos": [], "sugestoes": ["Manter tom caloroso e brasileiro", "Garantir acessibilidade nas cores", "Respeitar identidade visual Azul"]}')]
mock_client.messages.create.return_value = mock_response

import brand_advisor
brand_advisor.client = mock_client

# Now import and run the app
from app import flask_app

if __name__ == "__main__":
    flask_app.run(port=5000, threaded=True, debug=True)