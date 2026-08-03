package com.jarvis.chat.feature.ai.domain.model

sealed interface OutputGuardResultModel {

    data object Allowed : OutputGuardResultModel

    data class Blocked(val reasons: List<String>, val fallbackMessage: String) : OutputGuardResultModel
}
