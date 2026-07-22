package com.jarvis.chat.core.viewmodel

interface UiMapper<in State, out UiModel> {

    fun map(state: State): UiModel
}
