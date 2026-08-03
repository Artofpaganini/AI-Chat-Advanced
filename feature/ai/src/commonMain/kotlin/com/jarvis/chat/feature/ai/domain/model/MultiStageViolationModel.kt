package com.jarvis.chat.feature.ai.domain.model

enum class MultiStageViolationModel {
    S1_PARSE,
    S1_ROUTE_LEAKED,
    S1_REDFLAG_MISMATCH,
    S2_PARSE,
    S3_EMPTY,
}
