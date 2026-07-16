#!/usr/bin/env python3
"""Run Flask app with mocked Anthropic client (no API key needed)."""
import os
from unittest.mock import MagicMock

# Must set before importing brand_advisor
mock_client = MagicMock()
mock_response = MagicMock()
mock_response.stop_reason = 'end_turn'
mock_response.model = 'claude-opus-4-8-mock'
mock_response.content = [MagicMock(type='text', text='{"estado": "vermelho", "riscos": [{"diretriz": "tom_low_cost", "risco": "Campanha foca em preço baixo como argumento central", "categoria": "tom_low_cost", "severidade": "alto"}, {"diretriz": "pontualidade_absoluta", "risco": "Promete voos sempre no horário sem ressalvas", "categoria": "promessa_absoluta", "severidade": "alto"}, {"diretriz": "tom_de_voz", "risco": "Linguagem corporativa fria, sem calor humano", "categoria": "tom_voz", "severidade": "medio"}], "sugestoes": ["Reforçar experiência e cuidado, não preço", "Trocar \"sempre no horário\" por \"compromisso com pontualidade\"", "Usar tom mais próximo e acolhedor"]}')]
mock_client.messages.create.return_value = mock_response

import brand_advisor
brand_advisor.client = mock_client

# Now import and run the app
from app import flask_app

if __name__ == "__main__":
    flask_app.run(port=5000, threaded=True, debug=True)