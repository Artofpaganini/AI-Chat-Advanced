plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.chat"
    }

    sourceSets {
        commonMain.dependencies {
            api(projects.feature.ai)
            implementation(projects.feature.voice)
            implementation(projects.core.viewmodel)
            implementation(libs.compose.material3)
            implementation(libs.androidx.lifecycle.viewmodel)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.koin.core)
            implementation(libs.koin.compose.viewmodel)
            implementation(libs.text.to.speech)
            implementation(libs.text.to.speech.compose)
        }
    }
}
