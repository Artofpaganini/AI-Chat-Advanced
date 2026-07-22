plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.core.viewmodel"
    }

    sourceSets {
        commonMain.dependencies {
            api(libs.androidx.lifecycle.viewmodel)
            api(libs.kotlinx.coroutines.core)
        }
    }
}
