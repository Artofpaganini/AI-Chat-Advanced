package com.jarvis.chat.feature.settings.domain.repository

import com.jarvis.chat.feature.settings.domain.model.InferenceModeModel
import kotlinx.coroutines.flow.StateFlow

internal interface InferenceModeSettingsRepository {

    fun observeInferenceMode(): StateFlow<InferenceModeModel>

    fun saveInferenceMode(inferenceMode: InferenceModeModel)
}
