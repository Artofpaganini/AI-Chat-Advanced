package com.jarvis.chat.feature.chat.domain.mapper

import com.jarvis.chat.feature.ai.domain.model.ChatMessageModel
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel

internal const val MAX_CONTEXT_MESSAGES = 10
internal const val MAX_CONTEXT_CHARS = 8_000

internal fun HistoryMessageModel.toChatMessageModel(): ChatMessageModel =
    ChatMessageModel(
        author = if (isImportedUnverifiedAssistant) MessageAuthor.USER else author,
        text = text,
    )

internal fun List<HistoryMessageModel>.toRequestContext(): List<ChatMessageModel> {
    val recentMessages = takeLast(MAX_CONTEXT_MESSAGES)
    val trimmedMessages = mutableListOf<HistoryMessageModel>()
    var totalChars = 0
    for (message in recentMessages.asReversed()) {
        val nextTotalChars = totalChars + message.text.length
        if (nextTotalChars > MAX_CONTEXT_CHARS) {
            break
        }
        trimmedMessages.add(message)
        totalChars = nextTotalChars
    }
    if (trimmedMessages.isEmpty()) {
        val newestMessage = recentMessages.lastOrNull() ?: return emptyList()
        trimmedMessages.add(newestMessage.copy(text = newestMessage.text.take(MAX_CONTEXT_CHARS)))
    }
    return trimmedMessages.asReversed().map { message -> message.toChatMessageModel() }
}
