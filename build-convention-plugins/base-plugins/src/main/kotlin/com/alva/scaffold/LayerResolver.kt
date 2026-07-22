package com.alva.scaffold

// Разрешает итоговый набор слоёв feature-модуля из флагов.
// Зеркаль cmd_feature из scaffold.sh: приоритет layers= > with-viewmodel > full/no- > default.
object LayerResolver {

    private val validLayers = setOf("nav", "presentation", "domain", "data")

    fun resolve(
        full: Boolean,
        withViewModel: Boolean,
        layersCsv: String,
        noLayers: Set<String>,
    ): FeatureLayers {
        val hasExplicitLayers = layersCsv.isNotBlank()
        val hasNoLayers = noLayers.isNotEmpty()
        validateNoLayers(noLayers)
        if (hasExplicitLayers && (full || hasNoLayers)) {
            error("--layers= нельзя сочетать с --full или --no-<layer> (взаимоисключающие способы задания слоёв)")
        }
        if (hasExplicitLayers && withViewModel) {
            error("--layers= нельзя сочетать с --with-viewmodel")
        }
        if (full && withViewModel) {
            error("--full нельзя сочетать с --with-viewmodel")
        }
        return when {
            hasExplicitLayers -> fromExplicitLayers(layersCsv)
            withViewModel -> FeatureLayers(nav = true, presentation = true, domain = false, data = false)
            full || hasNoLayers -> fullMinus(noLayers)
            else -> FeatureLayers(nav = true, presentation = false, domain = false, data = false)
        }
    }

    private fun fromExplicitLayers(layersCsv: String): FeatureLayers {
        val requested = layersCsv.split(",").map { token -> token.trim() }.filter { token -> token.isNotEmpty() }
        requested.forEach { layer ->
            if (layer !in validLayers) {
                error("неизвестный слой '$layer' в --layers= (допустимы: nav, presentation, domain, data)")
            }
        }
        return FeatureLayers(
            nav = "nav" in requested,
            presentation = "presentation" in requested,
            domain = "domain" in requested,
            data = "data" in requested,
        )
    }

    private fun fullMinus(noLayers: Set<String>): FeatureLayers =
        FeatureLayers(
            nav = "nav" !in noLayers,
            presentation = "presentation" !in noLayers,
            domain = "domain" !in noLayers,
            data = "data" !in noLayers,
        )

    private fun validateNoLayers(noLayers: Set<String>) {
        noLayers.forEach { layer ->
            if (layer !in validLayers) {
                error("неизвестный слой '$layer' в --no-<layer> (допустимы: nav, presentation, domain, data)")
            }
        }
    }
}
