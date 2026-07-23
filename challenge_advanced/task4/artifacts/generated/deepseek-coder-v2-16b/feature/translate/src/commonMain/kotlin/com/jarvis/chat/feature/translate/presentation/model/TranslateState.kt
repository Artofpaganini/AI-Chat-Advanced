package com.jarvis.chat.feature.translate.presentation.model

internal data class TranslateState(
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)
