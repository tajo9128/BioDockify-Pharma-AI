import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.llm.adapters import LMStudioAdapter

class TestLMStudioDetection(unittest.TestCase):
    
    @patch('modules.llm.adapters.requests.get')
    def test_auto_detection_success(self, mock_get):
        """Test successful auto-detection of a preferred model."""
        # Mock API response from /v1/models
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "local-model-v1"},
                {"id": "TheBloke/OpenBioLLM-Llama3-8B-GGUF"}, # Preferred
                {"id": "mistral-instruct"}
            ]
        }
        mock_get.return_value = mock_response
        
        adapter = LMStudioAdapter(model="auto")
        detected = adapter._auto_select_model()
        
        print(f"Detected: {detected}")
        self.assertEqual(detected, "TheBloke/OpenBioLLM-Llama3-8B-GGUF")
        
    @patch('modules.llm.adapters.requests.get')
    def test_auto_detection_fallback(self, mock_get):
        """Test fallback to first available if no preferred model found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "random-model-v1"},
                {"id": "another-model"}
            ]
        }
        mock_get.return_value = mock_response
        
        adapter = LMStudioAdapter(model="auto")
        detected = adapter._auto_select_model()
        
        print(f"Fallbacked to: {detected}")
        self.assertEqual(detected, "random-model-v1")

    @patch('modules.llm.adapters.requests.get')
    def test_detection_failure(self, mock_get):
        """Test graceful failure when API is down."""
        mock_get.side_effect = Exception("Connection Refused")
        
        adapter = LMStudioAdapter(model="auto")
        detected = adapter._auto_select_model()
        
        print(f"Failure handling returned: {detected}")
        self.assertEqual(detected, "local-model")

if __name__ == '__main__':
    unittest.main()
