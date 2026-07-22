package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.domain.model.HistoryMessageModel
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel

internal class ChatUiMapper : UiMapper<ChatState, ChatUiModel> {

    override fun map(state: ChatState): ChatUiModel {
        val visibleMessages = if (state.isFavoritesFilterActive) {
            state.messages.filter { message -> message.isFavorite }
        } else {
            state.messages
        }
        return ChatUiModel(
            messages = visibleMessages.map { message -> message.toChatMessageUiModel() },
            inputText = state.inputText,
            isLoading = state.isLoading && !state.isFavoritesFilterActive,
            isSendEnabled = state.inputText.isNotBlank() && !state.isLoading,
            isErrorVisible = state.hasError && !state.isFavoritesFilterActive,
            isFavoritesFilterActive = state.isFavoritesFilterActive,
            favoritesCount = state.messages.count { message -> message.isFavorite },
        )
    }

    private fun HistoryMessageModel.toChatMessageUiModel(): ChatMessageUiModel {
        val isFromUser = author == MessageAuthor.USER
        return ChatMessageUiModel(
            id = id,
            text = text,
            isFromUser = isFromUser,
            isSpeakable = !isFromUser,
            isFavorite = isFavorite,
            canFavorite = !isFromUser,
        )
    }
}
