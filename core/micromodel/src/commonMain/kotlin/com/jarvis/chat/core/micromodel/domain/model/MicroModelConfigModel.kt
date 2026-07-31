package com.jarvis.chat.core.micromodel.domain.model

internal data class MicroModelConfigModel(
    val labels: List<MicroTriageRouteModel>,
    val analyzers: List<MicroModelAnalyzerModel>,
    val vocabulary: Map<String, MicroModelVocabularyEntryModel>,
    val bias: List<Double>,
    val weights: Map<Int, List<Double>>,
    val confidenceMinProb: Double,
    val confidenceMinMargin: Double,
    val alwaysEscalateLabels: Set<MicroTriageRouteModel>,
) {

    init {
        check(MicroTriageRouteModel.entries.all { route -> route in labels }) {
            "micro_model.json labels не содержат все четыре маршрута: $labels"
        }
        check(MicroTriageRouteModel.EMERGENCY in alwaysEscalateLabels) {
            "micro_model.json thresholds.always_escalate_labels не содержит EMERGENCY: $alwaysEscalateLabels"
        }
    }
}
