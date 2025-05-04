"""
Query rewriting utilities for improved RAG performance
"""
from typing import Dict, Any
from app.logging import get_logger
from app.stores.llm import LLMProviderInterface
from app.stores.llm.templates.template_parser import TemplateParser
from app.utils.nltk_processor import is_arabic_text, enhance_query

logger = get_logger(__name__)

class QueryRewriter:
    """
    Class for rewriting user queries to improve RAG retrieval performance
    """

    def __init__(self, llm_client: LLMProviderInterface, template_parser: TemplateParser = None):
        """
        Initialize the query rewriter

        Args:
            llm_client: LLM client for generating rewritten queries
            template_parser: Template parser for getting prompt templates
        """
        self.llm_client = llm_client

        # Create a new template parser if not provided
        # This ensures each QueryRewriter has its own template parser instance
        if template_parser is None:
            self.template_parser = TemplateParser()
        else:
            # Use a copy of the provided template parser to avoid modifying the original
            self.template_parser = TemplateParser(
                language=template_parser.language,
                default_language=template_parser.default_language
            )

    async def rewrite_query(self, original_query: str, knowledge_base_name: str = None,
                           language: str = None, is_cross_language: bool = None) -> Dict[str, Any]:
        """
        Rewrite a query to improve retrieval performance

        Args:
            original_query: The original user query
            knowledge_base_name: Optional name of the knowledge base for context
            language: Optional language of the query
            is_cross_language: Whether this is a cross-language search (e.g., Arabic query for English content)

        Returns:
            Dictionary containing original and rewritten queries
        """
        try:
            # Check if the query is in Arabic
            is_arabic = is_arabic_text(original_query)

            # If Arabic, use specialized Arabic processing
            if is_arabic and not language:
                logger.info(f"Detected Arabic query: '{original_query}'")
                language = "ar"

            # If is_cross_language is not explicitly set, assume cross-language search for Arabic queries
            if is_cross_language is None and is_arabic:
                is_cross_language = True
                logger.info("Assuming cross-language search (Arabic query for English content)")

            # Get the query rewriting prompt template
            prompt_vars = {
                "original_query": original_query,
                "knowledge_base": knowledge_base_name or "the knowledge base",
                "language": language or "the query's language"
            }

            # Get the appropriate prompt template
            prompt = self._get_rewrite_prompt(prompt_vars)

            # Generate the rewritten query
            rewritten_query = await self.llm_client.generate_text(prompt=prompt)

            # Clean up the response
            rewritten_query = self._clean_rewritten_query(rewritten_query)

            # Log the rewriting
            logger.info(f"Query rewriting: Original: '{original_query}' → Rewritten: '{rewritten_query}'")

            # For Arabic queries, enhance with NLTK processing
            if is_arabic:
                # Get enhanced query with NLTK
                arabic_result = enhance_query(original_query, None, 'ar')

                # Log the Arabic enhancement
                logger.debug(f"Arabic query enhancement: {arabic_result}")

                # Return with Arabic-specific information
                return {
                    "original_query": original_query,
                    "rewritten_query": rewritten_query,
                    "enhanced_query": arabic_result.get("enhanced_query"),
                    "is_arabic": True,
                    "success": True
                }

            # Return standard result for non-Arabic queries
            return {
                "original_query": original_query,
                "rewritten_query": rewritten_query,
                "is_arabic": False,
                "success": True
            }

        except Exception as e:
            logger.error(f"Error rewriting query: {str(e)}")
            # Check if query is Arabic even in error case
            is_arabic = False
            try:
                is_arabic = is_arabic_text(original_query)
            except:
                pass

            return {
                "original_query": original_query,
                "rewritten_query": original_query,  # Fall back to original query
                "is_arabic": is_arabic,
                "success": False,
                "error": str(e)
            }

    def _get_rewrite_prompt(self, vars: Dict[str, Any]) -> str:
        """
        Get the query rewriting prompt

        Args:
            vars: Variables to substitute in the template

        Returns:
            Formatted prompt string
        """
        # Check if this is an Arabic query (cross-language search)
        is_arabic = vars.get('language') == 'ar'

        # Try to get the regular template from the template parser
        if self.template_parser:
            template = self.template_parser.get_template("query", "rewrite_prompt", vars)
            if template:
                return template

        # Fall back to default templates based on language
        if is_arabic:
            # Default cross-language template for Arabic queries
            return f"""
أنت مساعد متخصص في البحث عبر اللغات (Cross-Language Information Retrieval).
مهمتك هي تحويل استفسار المستخدم باللغة العربية إلى استفسار يمكنه العثور على معلومات ذات صلة في مستندات باللغة الإنجليزية.

الاستفسار الأصلي باللغة العربية: "{vars['original_query']}"

سيتم استخدام الاستفسار للبحث في مستندات باللغة الإنجليزية في {vars['knowledge_base']}.

يرجى إنشاء استفسار محسّن يتضمن:
1. الاستفسار الأصلي باللغة العربية (للحفاظ على السياق)
2. ترجمة دقيقة للاستفسار إلى اللغة الإنجليزية
3. مصطلحات تقنية إضافية باللغة الإنجليزية ذات صلة بالموضوع
4. كلمات مفتاحية إنجليزية قد تظهر في المستندات المتعلقة بهذا الموضوع
5. مرادفات ومصطلحات بديلة باللغة الإنجليزية لتوسيع نطاق البحث

الرجاء الرد بالاستفسار المحسّن فقط، بدون أي شروحات أو بادئات أو علامات اقتباس.
يجب أن يتضمن الاستفسار المحسّن كلًا من النص العربي الأصلي والمصطلحات الإنجليزية ذات الصلة.
"""
        else:
            # Default template for other languages
            return f"""
You are an AI assistant helping to improve search queries for a retrieval system.
Your task is to rewrite the user's query to make it more effective for retrieving relevant information.

Original query: "{vars['original_query']}"

The query will be used to search in {vars['knowledge_base']}.

Please rewrite the query to:
1. Make it more specific and detailed
2. Include relevant keywords that might appear in the documents
3. Expand any acronyms or abbreviations
4. Break down complex questions into clearer search terms
5. Maintain the original intent and meaning

Respond ONLY with the rewritten query, without any explanations, prefixes, or quotes.
Keep the rewritten query in {vars['language']}.
"""

    def _clean_rewritten_query(self, query: str) -> str:
        """
        Clean up the rewritten query by removing quotes and other artifacts

        Args:
            query: The raw rewritten query from the LLM

        Returns:
            Cleaned query string
        """
        # Remove quotes if present
        query = query.strip('"\'')

        # Remove "Rewritten query:" prefix if present
        prefixes = ["Rewritten query:", "Rewritten Query:", "Query:"]
        for prefix in prefixes:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()

        return query.strip()
