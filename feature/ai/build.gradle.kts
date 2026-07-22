plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.kotlinx.serialization)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.ai"
    }

    sourceSets {
        commonMain.dependencies {
            api(libs.koin.core)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.ktor.client.core)
            implementation(libs.ktor.client.content.negotiation)
            implementation(libs.ktor.client.json)
        }

        androidMain.dependencies {
            implementation(libs.ktor.client.okhttp)
        }

        iosMain.dependencies {
            implementation(libs.ktor.client.darwin)
        }
    }
}
