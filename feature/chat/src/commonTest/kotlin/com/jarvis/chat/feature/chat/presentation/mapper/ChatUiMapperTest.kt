package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.feature.ai.domain.model.AiErrorModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.ai.domain.model.TriageModel
import com.jarvis.chat.feature.ai.domain.model.TriageRouteModel
import com.jarvis.chat.feature.ai.domain.model.TriageStatusModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.TriageRouteUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageStatusUiModel
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ChatUiMapperTest {

    private val mapper = ChatUiMapper()

    @Test
    fun map_emptyState_producesEmptyUiModelWithDefaults() {
        val uiModel = mapper.map(ChatState())

        assertTrue(uiModel.messages.isEmpty())
        assertEquals("", uiModel.inputText)
        assertFalse(uiModel.isLoading)
        assertFalse(uiModel.isSendEnabled)
        assertFalse(uiModel.isErrorVisible)
        assertFalse(uiModel.isFavoritesFilterActive)
        assertEquals(0, uiModel.favoritesCount)
        assertTrue(uiModel.isEmptyState)
        assertFalse(uiModel.isFavoritesEmptyState)
    }

    @Test
    fun map_userMessage_projectsAsFromUserAndNotFavoritable() {
        val state = ChatState(messages = listOf(userMessage(id = "u1", text = "hello")))

        val uiMessage = mapper.map(state).messages.single()

        assertEquals("u1", uiMessage.id)
        assertEquals("hello", uiMessage.text)
        assertTrue(uiMessage.isFromUser)
        assertFalse(uiMessage.isSpeakable)
        assertFalse(uiMessage.canFavorite)
    }

    @Test
    fun map_assistantMessage_projectsAsSpeakableAndFavoritable() {
        val state = ChatState(
            messages = listOf(assistantMessage(id = "a1", text = "hi there", isFavorite = true)),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertEquals("a1", uiMessage.id)
        assertFalse(uiMessage.isFromUser)
        assertTrue(uiMessage.isSpeakable)
        assertTrue(uiMessage.canFavorite)
        assertTrue(uiMessage.isFavorite)
    }

    @Test
    fun map_favoritesFilterActive_showsOnlyFavoriteMessages() {
        val state = ChatState(
            messages = listOf(
                userMessage(id = "u1", text = "question"),
                assistantMessage(id = "a1", text = "starred", isFavorite = true),
                assistantMessage(id = "a2", text = "plain", isFavorite = false),
            ),
            isFavoritesFilterActive = true,
        )

        val uiModel = mapper.map(state)

        assertEquals(listOf("a1"), uiModel.messages.map { message -> message.id })
        assertTrue(uiModel.isFavoritesFilterActive)
    }

    @Test
    fun map_favoritesCount_countsAllFavoritesRegardlessOfFilter() {
        val messages = listOf(
            assistantMessage(id = "a1", text = "one", isFavorite = true),
            assistantMessage(id = "a2", text = "two", isFavorite = true),
            assistantMessage(id = "a3", text = "three", isFavorite = false),
        )

        val withoutFilter = mapper.map(ChatState(messages = messages))
        val withFilter = mapper.map(ChatState(messages = messages, isFavoritesFilterActive = true))

        assertEquals(2, withoutFilter.favoritesCount)
        assertEquals(2, withFilter.favoritesCount)
    }

    @Test
    fun map_sendEnabled_requiresNonBlankInputAndNotLoading() {
        assertTrue(mapper.map(ChatState(inputText = "hi")).isSendEnabled)
        assertFalse(mapper.map(ChatState(inputText = "   ")).isSendEnabled)
        assertFalse(mapper.map(ChatState(inputText = "")).isSendEnabled)
        assertFalse(mapper.map(ChatState(inputText = "hi", isLoading = true)).isSendEnabled)
    }

    @Test
    fun map_loadingAndError_visibleOnlyWhenFilterInactive() {
        val active = ChatState(isLoading = true, error = AiErrorModel.Unknown, isFavoritesFilterActive = true)
        val inactive = ChatState(isLoading = true, error = AiErrorModel.Unknown, isFavoritesFilterActive = false)

        val activeUi = mapper.map(active)
        val inactiveUi = mapper.map(inactive)

        assertFalse(activeUi.isLoading)
        assertFalse(activeUi.isErrorVisible)
        assertTrue(inactiveUi.isLoading)
        assertTrue(inactiveUi.isErrorVisible)
    }

    @Test
    fun map_nonEmptyHistory_hidesEmptyState() {
        val state = ChatState(messages = listOf(userMessage(id = "u1", text = "hello")))

        val uiModel = mapper.map(state)

        assertFalse(uiModel.isEmptyState)
    }

    @Test
    fun map_loadingOrError_hidesEmptyState() {
        val loading = ChatState(isLoading = true)
        val errored = ChatState(error = AiErrorModel.Unknown)

        assertFalse(mapper.map(loading).isEmptyState)
        assertFalse(mapper.map(errored).isEmptyState)
    }

    @Test
    fun map_favoritesFilterActiveAndEmpty_showsFavoritesEmptyStateNotOnboarding() {
        val state = ChatState(isFavoritesFilterActive = true)

        val uiModel = mapper.map(state)

        assertFalse(uiModel.isEmptyState)
        assertTrue(uiModel.isFavoritesEmptyState)
    }

    @Test
    fun map_favoritesFilterActiveWithFavorites_hidesFavoritesEmptyState() {
        val state = ChatState(
            messages = listOf(assistantMessage(id = "a1", text = "starred", isFavorite = true)),
            isFavoritesFilterActive = true,
        )

        val uiModel = mapper.map(state)

        assertFalse(uiModel.isFavoritesEmptyState)
    }

    @Test
    fun map_userMessage_projectsTimestampAsHourMinuteTimeLabel() {
        val state = ChatState(messages = listOf(userMessage(id = "u1", text = "hello", timestamp = TEST_TIMESTAMP)))

        val uiMessage = mapper.map(state).messages.single()

        assertTrue(TIME_LABEL_REGEX.matches(uiMessage.timeLabel))
    }

    @Test
    fun map_zeroTimestamp_doesNotCrashAndProducesTimeLabel() {
        val state = ChatState(messages = listOf(userMessage(id = "u1", text = "legacy", timestamp = ZERO_TIMESTAMP)))

        val uiMessage = mapper.map(state).messages.single()

        assertTrue(TIME_LABEL_REGEX.matches(uiMessage.timeLabel))
    }

    @Test
    fun map_messagesWithDifferentAuthorsAndTimestamps_preservesMessageOrder() {
        val state = ChatState(
            messages = listOf(
                userMessage(id = "u1", text = "question", timestamp = TEST_TIMESTAMP),
                assistantMessage(id = "a1", text = "answer", isFavorite = false, timestamp = LATER_TEST_TIMESTAMP),
            ),
        )

        val uiModel = mapper.map(state)

        assertEquals(listOf("u1", "a1"), uiModel.messages.map { message -> message.id })
    }

    @Test
    fun map_isLoadingTrue_showsTypingIndicator() {
        val state = ChatState(isLoading = true)

        val uiModel = mapper.map(state)

        assertTrue(uiModel.isLoading)
    }

    @Test
    fun map_isLoadingFalse_hidesTypingIndicator() {
        val state = ChatState(isLoading = false)

        val uiModel = mapper.map(state)

        assertFalse(uiModel.isLoading)
    }

    @Test
    fun map_isLoadingTrue_setsGeneratingRegardlessOfFavoritesFilter() {
        val active = ChatState(isLoading = true, isFavoritesFilterActive = true)
        val inactive = ChatState(isLoading = true, isFavoritesFilterActive = false)

        assertTrue(mapper.map(active).isGenerating)
        assertTrue(mapper.map(inactive).isGenerating)
    }

    @Test
    fun map_isLoadingFalse_clearsGenerating() {
        val state = ChatState(isLoading = false)

        val uiModel = mapper.map(state)

        assertFalse(uiModel.isGenerating)
    }

    @Test
    fun map_everyAiErrorVariant_producesNonEmptyErrorMessage() {
        ALL_AI_ERROR_VARIANTS.forEach { error ->
            val uiModel = mapper.map(ChatState(error = error))

            assertTrue(uiModel.errorMessage.orEmpty().isNotEmpty(), "empty message for $error")
        }
    }

    @Test
    fun map_everyAiErrorVariant_producesDistinctErrorMessages() {
        val messages = ALL_AI_ERROR_VARIANTS.map { error -> mapper.map(ChatState(error = error)).errorMessage }

        assertEquals(ALL_AI_ERROR_VARIANTS.size, messages.toSet().size)
    }

    @Test
    fun map_serverError_includesErrorCodeInMessage() {
        val state = ChatState(error = AiErrorModel.ServerError(code = TEST_SERVER_ERROR_CODE))

        val uiModel = mapper.map(state)

        assertTrue(uiModel.errorMessage.orEmpty().contains(TEST_SERVER_ERROR_CODE.toString()))
    }

    @Test
    fun map_badRequest_includesApiMessageVerbatim() {
        val state = ChatState(error = AiErrorModel.BadRequest(message = TEST_BAD_REQUEST_MESSAGE))

        val uiModel = mapper.map(state)

        assertEquals(TEST_BAD_REQUEST_MESSAGE, uiModel.errorMessage)
    }

    @Test
    fun map_speakingMessageId_marksMatchingMessageAsSpeakingOnly() {
        val state = ChatState(
            messages = listOf(
                assistantMessage(id = "a1", text = "one", isFavorite = false),
                assistantMessage(id = "a2", text = "two", isFavorite = false),
            ),
            speakingMessageId = "a2",
        )

        val uiModel = mapper.map(state)

        assertFalse(uiModel.messages.first { message -> message.id == "a1" }.isSpeaking)
        assertTrue(uiModel.messages.first { message -> message.id == "a2" }.isSpeaking)
    }

    @Test
    fun map_noSpeakingMessageId_marksAllMessagesAsNotSpeaking() {
        val state = ChatState(messages = listOf(assistantMessage(id = "a1", text = "one", isFavorite = false)))

        val uiModel = mapper.map(state)

        assertFalse(uiModel.messages.single().isSpeaking)
    }

    @Test
    fun map_assistantMessageWithModelId_exposesModelIdOnUiModel() {
        val state = ChatState(
            messages = listOf(
                assistantMessage(id = "a1", text = "answer", isFavorite = false, modelId = "deepseek-chat"),
            ),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertEquals("deepseek-chat", uiMessage.modelId)
    }

    @Test
    fun map_assistantMessageWithoutModelId_leavesModelIdNull() {
        val state = ChatState(messages = listOf(assistantMessage(id = "a1", text = "answer", isFavorite = false)))

        val uiMessage = mapper.map(state).messages.single()

        assertEquals(null, uiMessage.modelId)
    }

    @Test
    fun map_assistantMessageWithBlankModelId_hidesModelId() {
        val state = ChatState(
            messages = listOf(assistantMessage(id = "a1", text = "answer", isFavorite = false, modelId = "   ")),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertEquals(null, uiMessage.modelId)
    }

    @Test
    fun map_userMessageWithModelId_neverExposesModelIdOnUiModel() {
        val state = ChatState(
            messages = listOf(userMessage(id = "u1", text = "question").copy(modelId = "deepseek-chat")),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertEquals(null, uiMessage.modelId)
    }

    @Test
    fun map_assistantMessageWithTriage_exposesTriageUiModel() {
        val triage = testTriage()
        val state = ChatState(
            messages = listOf(
                assistantMessage(id = "a1", text = "answer", isFavorite = false).copy(triage = triage),
            ),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertEquals(TriageRouteUiModel.EMERGENCY, uiMessage.triage?.route)
        assertEquals("Emergency", uiMessage.triage?.routeLabel)
        assertEquals(TriageStatusUiModel.OK, uiMessage.triage?.status)
        assertEquals("Checked", uiMessage.triage?.statusLabel)
        assertEquals(98, uiMessage.triage?.confidencePercent)
        assertEquals("why", uiMessage.triage?.explain)
    }

    @Test
    fun map_assistantMessageWithoutTriage_leavesTriageNull() {
        val state = ChatState(messages = listOf(assistantMessage(id = "a1", text = "answer", isFavorite = false)))

        val uiMessage = mapper.map(state).messages.single()

        assertNull(uiMessage.triage)
    }

    @Test
    fun map_userMessageWithTriage_neverExposesTriageOnUiModel() {
        val state = ChatState(
            messages = listOf(userMessage(id = "u1", text = "question").copy(triage = testTriage())),
        )

        val uiMessage = mapper.map(state).messages.single()

        assertNull(uiMessage.triage)
    }

    private fun testTriage(): TriageModel =
        TriageModel(
            route = TriageRouteModel.EMERGENCY,
            routeLabel = "Emergency",
            status = TriageStatusModel.OK,
            statusLabel = "Checked",
            confidence = 0.98,
            explain = "why",
            crisis = false,
        )

    private fun userMessage(id: String, text: String, timestamp: Long = TEST_TIMESTAMP): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.USER,
            text = text,
            isFavorite = false,
            timestamp = timestamp,
        )

    private fun assistantMessage(
        id: String,
        text: String,
        isFavorite: Boolean,
        timestamp: Long = TEST_TIMESTAMP,
        modelId: String? = null,
    ): HistoryMessageModel =
        HistoryMessageModel(
            id = id,
            author = MessageAuthor.ASSISTANT,
            text = text,
            isFavorite = isFavorite,
            timestamp = timestamp,
            modelId = modelId,
        )
}

private const val TEST_TIMESTAMP = 1_700_000_000_000L
private const val LATER_TEST_TIMESTAMP = 1_700_000_100_000L
private const val ZERO_TIMESTAMP = 0L
private const val TEST_SERVER_ERROR_CODE = 503
private const val TEST_BAD_REQUEST_MESSAGE = "model overloaded, retry later"
private val TIME_LABEL_REGEX = Regex("^\\d{2}:\\d{2}$")
private val ALL_AI_ERROR_VARIANTS = listOf(
    AiErrorModel.NoConnection,
    AiErrorModel.Timeout,
    AiErrorModel.Unauthorized,
    AiErrorModel.BadRequest(message = TEST_BAD_REQUEST_MESSAGE),
    AiErrorModel.RateLimited,
    AiErrorModel.ServerError(code = TEST_SERVER_ERROR_CODE),
    AiErrorModel.Unknown,
)
