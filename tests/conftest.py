import os
import sys
from unittest.mock import Mock, MagicMock, patch
import pytest

# Set environment variables before any imports
os.environ["LLAMA_USE_GPU"] = "0"

# Mock the transformers library before any imports
sys.modules['transformers'] = Mock()
sys.modules['transformers.AutoTokenizer'] = Mock()
sys.modules['transformers.AutoModelForCausalLM'] = Mock()

# Create mock tokenizer and model objects
mock_tokenizer = Mock()
mock_model = Mock()

# Setup mock AutoTokenizer.from_pretrained to return our mock tokenizer
mock_auto_tokenizer = Mock()
mock_auto_tokenizer.from_pretrained.return_value = mock_tokenizer

# Setup mock AutoModelForCausalLM.from_pretrained to return our mock model  
mock_auto_model = Mock()
mock_auto_model.from_pretrained.return_value = mock_model

# Replace the classes in the mocked module
sys.modules['transformers'].AutoTokenizer = mock_auto_tokenizer
sys.modules['transformers'].AutoModelForCausalLM = mock_auto_model

# Mock torch and other dependencies that might be problematic
sys.modules['torch'] = Mock()
sys.modules['torch'].cuda = Mock()
sys.modules['torch'].cuda.is_available.return_value = False
sys.modules['torch'].float16 = Mock()

# Mock other potentially problematic modules
sys.modules['gstop'] = Mock()
sys.modules['huggingface_hub'] = Mock()
sys.modules['llama_cpp'] = Mock()

# Mock dotenv
sys.modules['dotenv'] = Mock()

@pytest.fixture(autouse=True)
def setup_mocks():
    """Automatically setup mocks for all tests"""
    # This fixture runs automatically for all tests
    # Additional per-test setup can be done here if needed
    pass
