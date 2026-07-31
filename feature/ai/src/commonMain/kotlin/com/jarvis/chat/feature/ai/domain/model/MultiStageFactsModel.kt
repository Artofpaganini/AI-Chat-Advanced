package com.jarvis.chat.feature.ai.domain.model

data class MultiStageFactsModel(
    val ageMonths: Int?,
    val symptoms: List<String>,
    val metrics: String,
    val duration: String,
    val parentState: String,
    val questionType: MultiStageQuestionTypeModel,
)
