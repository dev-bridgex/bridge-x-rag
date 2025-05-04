from string import Template

#### QUERY REWRITING PROMPTS ####

# Arabic queries always use cross-language search (Arabic to English)
rewrite_prompt = Template("""
أنت مساعد متخصص في البحث عبر اللغات (Cross-Language Information Retrieval).
مهمتك هي تحويل استفسار المستخدم باللغة العربية إلى استفسار يمكنه العثور على معلومات ذات صلة في مستندات باللغة الإنجليزية.

الاستفسار الأصلي باللغة العربية: "$original_query"

سيتم استخدام الاستفسار للبحث في مستندات باللغة الإنجليزية في $knowledge_base.

يرجى إنشاء استفسار محسّن يتضمن:
1. الاستفسار الأصلي باللغة العربية (للحفاظ على السياق)
2. ترجمة دقيقة للاستفسار إلى اللغة الإنجليزية
3. مصطلحات تقنية إضافية باللغة الإنجليزية ذات صلة بالموضوع (على الأقل 10 مصطلحات)
4. كلمات مفتاحية إنجليزية قد تظهر في المستندات المتعلقة بهذا الموضوع
5. مرادفات ومصطلحات بديلة باللغة الإنجليزية لتوسيع نطاق البحث

هام جداً:
- يجب أن تكون المصطلحات الإنجليزية أكثر من المصطلحات العربية في الاستفسار المحسّن
- يجب أن تتضمن على الأقل 15-20 كلمة باللغة الإنجليزية
- تأكد من تضمين جميع المصطلحات التقنية المتعلقة بالموضوع باللغة الإنجليزية
- استخدم المصطلحات الإنجليزية الشائعة التي يمكن أن تظهر في المستندات التقنية

مثال 1:
إذا كان الاستفسار "ما هي مبادئ البرمجة الشيئية"، يجب تحويله إلى:
"ما هي مبادئ البرمجة الشيئية what are the principles of object-oriented programming OOP fundamentals concepts classes objects inheritance encapsulation polymorphism abstraction interfaces methods properties constructors destructors SOLID design patterns reusability modularity"

مثال 2:
إذا كان الاستفسار "كيف تعمل الشبكات العصبية"، يجب تحويله إلى:
"كيف تعمل الشبكات العصبية how do neural networks work artificial intelligence machine learning deep learning neurons activation functions backpropagation weights biases layers perceptron CNN RNN LSTM GAN transformer supervised unsupervised reinforcement learning"

الرجاء الرد بالاستفسار المحسّن فقط، بدون أي شروحات أو بادئات أو علامات اقتباس.
يجب أن يتضمن الاستفسار المحسّن كلًا من النص العربي الأصلي والعديد من المصطلحات الإنجليزية ذات الصلة.
""")
