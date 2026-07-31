package com.jarvis.chat.feature.ai.domain.model

fun interface InferenceModeProvider {

    fun currentMode(): InferenceModeModel
}
