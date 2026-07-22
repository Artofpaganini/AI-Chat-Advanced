package com.jarvis.chat.feature.chat.presentation.mapper

import com.jarvis.chat.core.viewmodel.UiMapper
import com.jarvis.chat.feature.ai.domain.model.MessageAuthor
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.ChatState
import com.jarvis.chat.feature.chat.presentation.model.ChatUiModel

internal class ChatUiMapper : UiMapper<ChatState, ChatUiModel> {

    override fun map(state: ChatState): ChatUiModel =
        ChatUiModel(
            messages = state.messages.mapIndexed { index, message ->
                val isFromUser = message.author == MessageAuthor.USER
                ChatMessageUiModel(
                    id = index,
                    text = message.text,
                    isFromUser = isFromUser,
                    isSpeakable = !isFromUser,
                )
            },
            inputText = state.inputText,
            isLoading = state.isLoading,
            isSendEnabled = state.inputText.isNotBlank() && !state.isLoading,
            isErrorVisible = state.hasError,
        )
}
