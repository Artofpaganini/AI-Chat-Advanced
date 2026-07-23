package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.feature.translate.domain.model.TranslationModel

internal data class TranslateState(
    val translation: TranslationModel? = null,
    val isLoading: Boolean = false,
    val error: String? = null,
)
