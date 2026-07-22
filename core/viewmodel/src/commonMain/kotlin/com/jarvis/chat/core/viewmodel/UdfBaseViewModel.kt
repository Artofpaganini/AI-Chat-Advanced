package com.jarvis.chat.core.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

abstract class UdfBaseViewModel<Action, UiState, State, Event>(
    initialState: State,
    uiMapper: UiMapper<State, UiState>,
) : ViewModel() {

    private val stateFlow = MutableStateFlow(initialState)

    private val eventChannel = Channel<Event>(Channel.BUFFERED)

    protected val currentState: State
        get() = stateFlow.value

    val uiState: StateFlow<UiState> = stateFlow
        .map { state -> uiMapper.map(state) }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = uiMapper.map(initialState),
        )

    val events: Flow<Event> = eventChannel.receiveAsFlow()

    abstract fun onAction(action: Action)

    protected fun updateState(reducer: State.() -> State) {
        stateFlow.update(reducer)
    }

    protected fun postEvent(event: Event) {
        viewModelScope.launch {
            eventChannel.send(event)
        }
    }
}
