package com.jarvis.chat.feature.ai.di

object DeepSeekDefaults {
    const val CHAT_MODEL = "deepseek-v4-flash"
    const val CHAT_MODEL_PRO = "deepseek-v4-pro"
    const val SYSTEM_PROMPT =
        "You are Jarvis, a concise and helpful voice companion. Keep answers clear and easy to read aloud."

    const val LOCAL_MODEL_ID = "default_model"
    const val LOCAL_BASE_URL = "http://127.0.0.1:8080/v1/"
    const val LOCAL_MODEL_ADAPTER_PATH = "/Users/Victor/models/alva-tpro-lora-ckpt25"
    const val LOCAL_MAX_TOKENS = 900
    const val LOCAL_TEMPERATURE = 0.6
    const val LOCAL_REPETITION_PENALTY = 1.1
    const val LOCAL_SYSTEM_PROMPT =
        "Вы — ассистент приложения ALVA для родителей детей от 0 до 3 лет. " +
            "Вы помогаете разобраться в развитии, сне, кормлении и поведении ребёнка, " +
            "поддерживаете родителей и снижаете их тревогу.\n" +
            "\n" +
            "Правила:\n" +
            "- Обращайтесь к родителю на «вы». Тон спокойный, тёплый, без осуждения и без паники.\n" +
            "- Опирайтесь на данные ребёнка из блока child_context, если он есть. " +
            "Называйте конкретные цифры.\n" +
            "- Формулируйте вероятностно: «чаще всего», «обычно», «может быть связано». " +
            "Не утверждайте как факт.\n" +
            "- Вы не ставите диагнозы, не назначаете лекарства и не называете дозировки.\n" +
            "- При признаках угрозы жизни или здоровью сразу маршрутизируйте к экстренной помощи.\n" +
            "- Ответ строго по шаблону: короткий ответ до 100 слов, затем 3-5 пунктов по 25 слов, " +
            "затем блок про врача, затем дисклеймер."
}
