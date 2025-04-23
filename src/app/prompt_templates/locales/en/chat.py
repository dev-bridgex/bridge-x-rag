from string import Template

"""
Chat Prompt Templates for English Locale

This file contains templates for the chat system with RAG capabilities.
Templates are used to format prompts for the LLM, including system instructions,
document formatting, and response generation.

Usage:
    from app.prompt_templates.locales.en.chat import system_prompt_rag, system_prompt_basic, document_prompt, context_prompt
    from string import Template

    # Render a template with variables
    system_prompt_text = system_prompt_rag.safe_substitute({})
    document_text = document_prompt.safe_substitute({
        'doc_number': 1,
        'doc_name': 'example.pdf',
        'chunk_text': 'This is the content of the document chunk.'
    })
"""

#### CHAT PROMPTS ####

#### System Prompts ####

# System prompt for RAG-enabled chat
system_prompt_rag = Template(
    "\n".join([
        "You are a helpful assistant that answers questions based on the user's knowledge base.",
        "You will be provided with relevant documents from the knowledge base to help answer the user's questions.",
        "Always maintain a conversational and helpful tone.",
        "If you don't know the answer or don't have enough information, be honest about it.",
        "Keep your responses concise and to the point.",
        "When appropriate, cite the specific documents you used in your response.",
        "Respond in the same language as the user's query."
    ])
)

# System prompt for basic chat (without RAG)
system_prompt_basic = Template(
    "\n".join([
        "You are a helpful assistant that answers questions in a conversational manner.",
        "Maintain a friendly and helpful tone in your responses.",
        "If you don't know the answer, be honest about it.",
        "Keep your responses concise and to the point.",
        "Respond in the same language as the user's query."
    ])
)

#### Document Formatting ####

# Format for individual documents
document_prompt = Template(
    "\n".join([
        "Document $doc_number: $doc_name",
        "Content: $chunk_text",
        ""
    ])
)

# Context message with retrieved documents
context_prompt = Template(
    "\n".join([
        "I've found the following information that might help answer the user's question:",
        "",
        "$documents",
        "",
        "Use this information to provide a helpful response to the user's question.",
        "If the information doesn't fully address the question, acknowledge this and provide what you can."
    ])
)

#### Response Formatting ####

# Format for responses that cite sources
response_with_sources_prompt = Template(
    "\n".join([
        "$response",
        "",
        "Sources:",
        "$sources"
    ])
)

# Format for follow-up suggestions
follow_up_suggestions_prompt = Template(
    "\n".join([
        "",
        "You might also want to ask about:",
        "$suggestions"
    ])
)
