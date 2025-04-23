from string import Template

"""
RAG Prompt Templates for English Locale

This file contains templates for the RAG (Retrieval-Augmented Generation) system.
Templates are used to format prompts for the LLM, including system instructions,
document formatting, and response generation.

Usage:
    from app.prompt_templates.locales.en.rag import system_prompt, document_prompt, footer_prompt
    from string import Template

    # Render a template with variables
    system_prompt_text = system_prompt.safe_substitute({})
    document_text = document_prompt.safe_substitute({
        'doc_number': 1,
        'doc_name': 'example.pdf',
        'source_path': '/documents/example.pdf',
        'page_number': 5,
        'chunk_order': 3,
        'content_type': 'text/pdf',
        'score': 0.95,
        'chunk_text': 'This is the content of the document chunk.'
    })
"""

#### RAG PROMPTS ####

#### System ####

system_prompt = Template(
    "\n".join([
        "You are an assistant to generate a response for the user.",
        "You will be provided with a set of documents associated with the user's query.",
        "Each document includes metadata such as document name, source path, page number, and relevance score.",
        "Generate a response based on the documents provided, focusing on the most relevant ones (higher scores).",
        "Ignore documents that are not relevant to the user's query.",
        "If you cannot generate a helpful response from the provided documents, politely explain this to the user.",
        "Generate the response in the same language as the user's query.",
        "Be polite, respectful, precise, and concise in your response.",
        "When appropriate, cite the specific documents you used by referring to their document numbers.",
    ])
)

#### Document ####
document_prompt = Template(
    "\n".join([
        "## Document Number: $doc_number",
        "## Document: $doc_name",
        "## Source Details:",
        "   Source Path/URL: $source_path",
        "   Page Number: $page_number",
        "   Chunk Number: $chunk_order",
        "   Content Type: $content_type",
        "## Relevance Score: $score",
        "### Content: $chunk_text",
        "###"
    ])
)


#### Footer ####

footer_prompt = Template(
    "\n".join([
    "Based only on the above documents, please generate an answer for the user.",
    "If the documents don't contain relevant information, acknowledge this and suggest what might help.",
    "When citing information, mention the document number (e.g., 'According to Document 1...').",
    "",
    "## Question:",
    "$query",
    "",
    "## Answer:",
    ])
)


#### No Documents Found ####

no_documents_prompt = Template(
    "\n".join([
    "I couldn't find any relevant documents in our knowledge base that match your query about '$query'.",
    "Here are some suggestions:",
    "1. Try rephrasing your question with different keywords",
    "2. Check if your question is related to topics covered in our knowledge base",
    "3. Be more specific about what you're looking for",
    "4. If you believe this information should be available, please let us know so we can improve our system",
    ])
)


#### Documents Wrapper ####

documents_wrapper_prompt = Template(
    "\n".join([
    "Below are $doc_count relevant documents from the knowledge base that might help answer your question:",
    "",
    "$documents",
    "",
    "---",
    ])
)


#### Citation Format ####

citation_format_prompt = Template(
    "\n".join([
    "[Document $doc_number: $doc_name]",
    ])
)


#### Follow-up Questions ####

follow_up_questions_prompt = Template(
    "\n".join([
    "",
    "## Follow-up Questions:",
    "Here are some follow-up questions you might consider asking:",
    "$follow_up_questions",
    ])
)


#### Content Type Specific Templates ####

# Template for code snippets
code_document_prompt = Template(
    "\n".join([
    "## Document Number: $doc_number",
    "## Document: $doc_name",
    "## Source Details:",
    "   Source Path: $source_path",
    "   Language: $language",
    "   Line Numbers: $line_numbers",
    "## Relevance Score: $score",
    "### Code Content:",
    "```$language",
    "$chunk_text",
    "```",
    "###"
    ])
)

# Template for tabular data
table_document_prompt = Template(
    "\n".join([
    "## Document Number: $doc_number",
    "## Document: $doc_name",
    "## Source Details:",
    "   Source Path: $source_path",
    "   Table Name: $table_name",
    "   Columns: $columns",
    "## Relevance Score: $score",
    "### Table Content:",
    "$chunk_text",
    "###"
    ])
)