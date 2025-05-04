from string import Template

#### QUERY REWRITING PROMPTS ####

rewrite_prompt = Template("""
You are an AI assistant helping to improve search queries for a retrieval system.
Your task is to rewrite the user's query to make it more effective for retrieving relevant information.

Original query: "$original_query"

The query will be used to search in $knowledge_base.

Please rewrite the query to:
1. Make it more specific and detailed
2. Include relevant keywords that might appear in the documents
3. Expand any acronyms or abbreviations
4. Break down complex questions into clearer search terms
5. Maintain the original intent and meaning

Respond ONLY with the rewritten query, without any explanations, prefixes, or quotes.
Keep the rewritten query in the same language as the original query.
""")
