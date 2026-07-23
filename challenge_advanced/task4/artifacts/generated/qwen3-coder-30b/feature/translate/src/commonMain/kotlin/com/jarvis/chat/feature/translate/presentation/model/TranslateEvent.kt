package com.jarvis.chat.feature.translate.presentation.model

import com.jarvis.chat.core.viewmodel.Event

internal sealed interface TranslateEvent : Event {
    data class ShowError(val message: String) : TranslateEvent
}
