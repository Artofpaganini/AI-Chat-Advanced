package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.feature.chat.domain.model.ChatSessionModel
import com.jarvis.chat.feature.chat.presentation.model.SessionsState
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class SessionsUiMapperTest {

    private val mapper = SessionsUiMapper()

    @Test
    fun map_emptyState_producesEmptyListAndHiddenSheet() {
        val uiModel = mapper.map(SessionsState())

        assertTrue(uiModel.sessions.isEmpty())
        assertFalse(uiModel.isSheetVisible)
        assertFalse(uiModel.isRenameDialogVisible)
        assertFalse(uiModel.isDeleteConfirmationVisible)
    }

    @Test
    fun map_sortsSessionsByLastMessageAtDescending() {
        val state = SessionsState(
            sessions = listOf(
                session(id = "s1", lastMessageAt = 100L),
                session(id = "s2", lastMessageAt = 300L),
                session(id = "s3", lastMessageAt = 200L),
            ),
        )

        val uiModel = mapper.map(state)

        assertEquals(listOf("s2", "s3", "s1"), uiModel.sessions.map { session -> session.id })
    }

    @Test
    fun map_blankTitle_showsNewChatPlaceholder() {
        val state = SessionsState(sessions = listOf(session(id = "s1", title = "")))

        val uiModel = mapper.map(state)

        assertEquals("New chat", uiModel.sessions.single().title)
    }

    @Test
    fun map_activeSessionId_marksMatchingSessionActiveOnly() {
        val state = SessionsState(
            sessions = listOf(session(id = "s1"), session(id = "s2")),
            activeSessionId = "s2",
        )

        val uiModel = mapper.map(state)

        assertFalse(uiModel.sessions.first { session -> session.id == "s1" }.isActive)
        assertTrue(uiModel.sessions.first { session -> session.id == "s2" }.isActive)
    }

    @Test
    fun map_pendingRenameSessionId_showsRenameDialogWithTitle() {
        val state = SessionsState(pendingRenameSessionId = "s1", pendingRenameTitle = "Draft title")

        val uiModel = mapper.map(state)

        assertTrue(uiModel.isRenameDialogVisible)
        assertEquals("Draft title", uiModel.renameTitle)
    }

    @Test
    fun map_pendingDeleteSessionId_showsDeleteConfirmation() {
        val state = SessionsState(pendingDeleteSessionId = "s1")

        val uiModel = mapper.map(state)

        assertTrue(uiModel.isDeleteConfirmationVisible)
    }

    private fun session(
        id: String,
        title: String = "Chat $id",
        lastMessageAt: Long = 0L,
    ): ChatSessionModel =
        ChatSessionModel(
            id = id,
            title = title,
            createdAt = 0L,
            lastMessageAt = lastMessageAt,
            messageCount = 0,
        )
}
