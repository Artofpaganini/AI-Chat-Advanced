package com.jarvis.chat.core.micromodel.domain.usecase

import com.jarvis.chat.core.micromodel.domain.model.MicroTriageModel
import com.jarvis.chat.core.micromodel.domain.repository.MicroModelRepository

class ClassifyMessageUseCase internal constructor(
    private val repository: MicroModelRepository,
) {

    suspend operator fun invoke(text: String): MicroTriageModel? = repository.classify(text)
}
