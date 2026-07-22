plugins {
    alias(libs.plugins.kmm) apply(false)
    alias(libs.plugins.android.application).apply(false)
    alias(libs.plugins.android.library).apply(false)
    alias(libs.plugins.android.kmp.library).apply(false)
    alias(libs.plugins.compose).apply(false)
    alias(libs.plugins.compose.compiler).apply(false)
    alias(libs.plugins.kotlinx.serialization).apply(false)
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.cocoapods).apply(false)
    alias(libs.plugins.internal.ktlint.setup) apply true
    alias(libs.plugins.internal.detekt.setup) apply true
}
