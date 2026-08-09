package com.jarvis.chat.feature.ai.domain.model

enum class CodeLoopStageModel {
    GENERATE,
    LINT,
    BUILD,
    SECURITY,
    COMMIT,
    RESULT,
    UNKNOWN,
}
