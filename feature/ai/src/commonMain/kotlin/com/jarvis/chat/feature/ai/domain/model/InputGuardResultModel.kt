package com.jarvis.chat.feature.ai.domain.model

sealed interface InputGuardResultModel {

    data object Allowed : InputGuardResultModel

    data class Blocked(val reason: String) : InputGuardResultModel
}
