from string import Template

"""
RAG Prompt Templates for English Locale

This file contains templates for the RAG (Retrieval-Augmented Generation) system.
Templates are used to format prompts for the LLM, including system instructions,
document formatting, and response generation.
"""

#### RAG PROMPTS ####

#### System ####

system_prompt = Template(
    "\n".join([
        "أنت مساعد لتوليد رد للمستخدم",
        "ستحصل على مجموعة من المستندات المرتبطة باستفسار المستخدم",
        "عليك توليد رد بناءً على المستندات المقدمة",
        "تجاهل المستندات التي لا تتعلق باستفسار المستخدم",
        "يمكنك الاعتذار للمستخدم إذا لم تتمكن من توليد رد",
        "عليك توليد الرد بنفس لغة استفسار المستخدم",
        "كن مؤدباً ومحترماً في التعامل مع المستخدم",
        "كن دقيقًا ومختصرًا في ردك. تجنب المعلومات غير الضرورية",
    ])
)


#### Document ####
document_prompt = Template(
    "\n".join([
        "## رقم المستند: $doc_number",
        "## المستند: $doc_name",
        "## تفاصيل المصدر:",
        "   مسار المصدر/الرابط: $source_path",
        "   رقم الصفحة: $page_number",
        "## درجة الصلة: $score",
        "### المحتوى: $chunk_text",
        "###"
    ])
)
#### Footer ####
footer_prompt = Template(
    "\n".join([
        "بناءً فقط على المستندات المذكورة أعلاه، قم بتوليد إجابة للمستخدم.",
        "إذا لم تحتوي المستندات على معلومات ذات صلة، اعترف بذلك واقترح ما قد يساعد.",
        "عند الاستشهاد بالمعلومات، اذكر رقم المستند (مثال: 'وفقًا للمستند 1...').",
        "",
        "## السؤال:",
        "$query",
        "",
        "## الإجابة:",
    ])
)