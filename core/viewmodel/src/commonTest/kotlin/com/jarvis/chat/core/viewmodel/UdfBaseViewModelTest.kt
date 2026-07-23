package com.jarvis.chat.core.viewmodel

import app.cash.turbine.test
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlin.test.AfterTest
import kotlin.test.BeforeTest
import kotlin.test.Test
import kotlin.test.assertEquals

class UdfBaseViewModelTest {

    @BeforeTest
    fun setUp() {
        Dispatchers.setMain(UnconfinedTestDispatcher())
    }

    @AfterTest
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun uiState_startsFromMappedInitialState() = runTest {
        val viewModel = CounterViewModel(initialCount = 3)

        assertEquals("count=3", viewModel.uiState.value)
    }

    @Test
    fun updateState_projectsNewStateThroughMapper() = runTest {
        val viewModel = CounterViewModel(initialCount = 0)

        viewModel.onAction(CounterAction.Increment)

        assertEquals("count=1", viewModel.uiState.value)
    }

    @Test
    fun updateState_appliedRepeatedly_accumulates() = runTest {
        val viewModel = CounterViewModel(initialCount = 0)

        repeat(5) { viewModel.onAction(CounterAction.Increment) }

        assertEquals("count=5", viewModel.uiState.value)
    }

    @Test
    fun updateState_readsCurrentStateForReducer() = runTest {
        val viewModel = CounterViewModel(initialCount = 10)

        viewModel.onAction(CounterAction.Double)

        assertEquals("count=20", viewModel.uiState.value)
    }

    @Test
    fun postEvent_deliversEventToCollector() = runTest {
        val viewModel = CounterViewModel(initialCount = 0)

        viewModel.events.test {
            viewModel.onAction(CounterAction.Notify("done"))

            assertEquals(CounterEvent.Message("done"), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun postEvent_bufferedBeforeCollection_isNotLost() = runTest {
        val viewModel = CounterViewModel(initialCount = 0)

        viewModel.onAction(CounterAction.Notify("first"))

        viewModel.events.test {
            assertEquals(CounterEvent.Message("first"), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    @Test
    fun events_preserveEmissionOrder() = runTest {
        val viewModel = CounterViewModel(initialCount = 0)

        viewModel.onAction(CounterAction.Notify("one"))
        viewModel.onAction(CounterAction.Notify("two"))

        viewModel.events.test {
            assertEquals(CounterEvent.Message("one"), awaitItem())
            assertEquals(CounterEvent.Message("two"), awaitItem())
            cancelAndIgnoreRemainingEvents()
        }
    }

    private data class CounterState(val count: Int)

    private sealed interface CounterAction {
        data object Increment : CounterAction
        data object Double : CounterAction
        data class Notify(val text: String) : CounterAction
    }

    private sealed interface CounterEvent {
        data class Message(val text: String) : CounterEvent
    }

    private class CounterUiMapper : UiMapper<CounterState, String> {
        override fun map(state: CounterState): String = "count=${state.count}"
    }

    private class CounterViewModel(
        initialCount: Int,
    ) : UdfBaseViewModel<CounterAction, String, CounterState, CounterEvent>(
        initialState = CounterState(count = initialCount),
        uiMapper = CounterUiMapper(),
    ) {

        override fun onAction(action: CounterAction) {
            when (action) {
                is CounterAction.Increment -> updateState { copy(count = count + 1) }
                is CounterAction.Double -> updateState { copy(count = currentState.count * 2) }
                is CounterAction.Notify -> postEvent(CounterEvent.Message(action.text))
            }
        }
    }
}
