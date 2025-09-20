"""Configuration file for model settings"""

# Model Configuration 
# Using DeepSeek API with OpenAI-compatible interface
# for more information on the models, see https://github.com/camel-ai/camel/blob/master/camel/types/enums.py

PLATFORM_TYPE = "OPENAI"  # DeepSeek uses OpenAI-compatible API
MODEL_TYPE = "GPT_4O"     # Use compatible model type

# Model Settings - optimized for DeepSeek
MODEL_CONFIG = {
    "temperature": 0.1,    # Lower temperature for more consistent responses
    "max_tokens": 8000,    # Higher token limit for DeepSeek
    "base_url": "https://api.deepseek.com/v1",  # DeepSeek API endpoint
}

# Agent Settings
MESSAGE_WINDOW_SIZE = 8000 * 50  # Increased for larger context
TOKEN_LIMIT = 32000              # Higher limit for DeepSeek 