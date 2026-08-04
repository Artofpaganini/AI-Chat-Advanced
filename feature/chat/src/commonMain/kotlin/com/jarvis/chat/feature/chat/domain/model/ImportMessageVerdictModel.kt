package com.jarvis.chat.feature.chat.domain.model

internal sealed interface ImportMessageVerdictModel {

    data class Accepted(val message: HistoryMessageModel, val wasTruncated: Boolean) : ImportMessageVerdictModel

    data class Rejected(val reason: ImportRejectionReasonModel) : ImportMessageVerdictModel
}
