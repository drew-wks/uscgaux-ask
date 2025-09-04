"""Factory function to create chat models based on TOML configuration."""
import os 
from typing import Mapping, Any
import logging
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama  # to test other LLMs



logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def create_chat_model(config: Mapping[str, Any]):
    """Create appropriate chat model based on configuration.
    
    Args:
        config: Configuration mapping containing RAG_ALL section with:
            - langchain_chat_model: "ChatOpenAI" or "ChatOllama"
            - generation_model: Model name (e.g., "gpt-4o-mini" or "deepseek-r1:8b")
            - temperature: Temperature setting
            - Additional model-specific parameters
    
    Returns:
        Configured chat model instance (ChatOpenAI or ChatOllama)
        
    Raises:
        ValueError: If unsupported chat model type is specified
    """
    
    rag_config = config["RAG_ALL"]
    chat_model_type = rag_config["langchain_chat_model"]
    model_name = rag_config["generation_model"]
    temperature = rag_config["temperature"]
    
    if chat_model_type == "ChatOpenAI":
        
        # Config langchain_openai for langchain_openai.OpenAIEmbeddings
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY_ASK"] # for openai client in cloud environment

        kwargs = {
            "model": model_name,
            "temperature": temperature
        }
        # Add optional OpenAI-specific parameters
        if "max_retries" in rag_config:
            kwargs["max_retries"] = rag_config["max_retries"]
        if "timeout" in rag_config:
            kwargs["timeout"] = rag_config["timeout"]
        
        logger.info(f"Initiated: {chat_model_type}")
        return ChatOpenAI(**kwargs)
        
    elif chat_model_type == "ChatOllama":
        kwargs = {
            "model": model_name,
            "temperature": temperature
        }
        # Add client_kwargs if present
        if "client_kwargs" in rag_config:
            kwargs["client_kwargs"] = rag_config["client_kwargs"]
        logger.info(f"Initiated: {chat_model_type}")
        return ChatOllama(**kwargs)
        
    else:
        raise ValueError(f"Unsupported chat model type: {chat_model_type}")

