package com.jarvis.chat.feature.chat.domain.model

internal enum class ImportRejectionReasonModel {
    FILE_TOO_LARGE,
    TOO_MANY_MESSAGES,
    HIDDEN_MARKUP,
    DENSE_INVISIBLE_CHARS,
    INPUT_GUARD_BLOCKED,
}
