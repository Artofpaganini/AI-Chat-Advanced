package com.jarvis.chat.feature.chat.data.mapper

import com.jarvis.chat.feature.chat.data.model.ChatSessionDataModel
import com.jarvis.chat.feature.chat.data.model.ChatSessionsIndexDataModel
import kotlin.test.Test
import kotlin.test.assertEquals

class ChatSessionDataMapperTest {

    @Test
    fun toChatSessionModel_preservesAllFields() {
        val dataModel = ChatSessionDataModel(
            id = "session-1",
            title = "Trip plan",
            createdAt = 1L,
            lastMessageAt = 2L,
            messageCount = 3,
        )

        val model = dataModel.toChatSessionModel()

        assertEquals("session-1", model.id)
        assertEquals("Trip plan", model.title)
        assertEquals(1L, model.createdAt)
        assertEquals(2L, model.lastMessageAt)
        assertEquals(3, model.messageCount)
    }

    @Test
    fun toChatSessionsModel_preservesSessionsAndActiveSessionId() {
        val index = ChatSessionsIndexDataModel(
            version = 1,
            sessions = listOf(
                ChatSessionDataModel(id = "session-1", title = "First", createdAt = 1L, lastMessageAt = 2L, messageCount = 1),
                ChatSessionDataModel(id = "session-2", title = "Second", createdAt = 3L, lastMessageAt = 4L, messageCount = 2),
            ),
            activeSessionId = "session-2",
        )

        val model = index.toChatSessionsModel()

        assertEquals(listOf("session-1", "session-2"), model.sessions.map { session -> session.id })
        assertEquals("session-2", model.activeSessionId)
    }
}
