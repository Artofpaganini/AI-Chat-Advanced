plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.voice"
    }

    sourceSets {
        commonMain.dependencies {
            api(libs.kotlinx.coroutines.core)
        }

        androidMain.dependencies {
            implementation(libs.androidx.activity.compose)
        }
    }
}
