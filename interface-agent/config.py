"""Configuration file for model settings"""

# Model Configuration 
# Using OpenAI API
# for more information on the models, see https://github.com/camel-ai/camel/blob/master/camel/types/enums.py

PLATFORM_TYPE = "OPENAI"
MODEL_TYPE = "GPT_4O_MINI"

# Model Settings
MODEL_CONFIG = {
    "temperature": 0.1,
    "max_tokens": 4000,
}

# Agent Settings
MESSAGE_WINDOW_SIZE = 4000 * 50
TOKEN_LIMIT = 16000 