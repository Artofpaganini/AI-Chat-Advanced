package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal const val MAX_CONTEXT_MESSAGES = 10
internal const val MAX_CONTEXT_CHARS = 8_000

internal fun HistoryMessageModel.toChatMessageModel(): ChatMessageModel =
    ChatMessageModel(
        author = author,
        text = text,
    )

internal fun List<HistoryMessageModel>.toRequestContext(): List<ChatMessageModel> {
    val recentMessages = takeLast(MAX_CONTEXT_MESSAGES)
    val trimmedMessages = mutableListOf<HistoryMessageModel>()
    var totalChars = 0
    for (message in recentMessages.asReversed()) {
        val nextTotalChars = totalChars + message.text.length
        if (trimmedMessages.isNotEmpty() && nextTotalChars > MAX_CONTEXT_CHARS) {
            break
        }
        trimmedMessages.add(message)
        totalChars = nextTotalChars
    }
    return trimmedMessages.asReversed().map { message -> message.toChatMessageModel() }
}
