plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
    alias(libs.plugins.kotlinx.serialization)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.chat"
        withHostTest {}
    }

    sourceSets {
        commonMain.dependencies {
            api(projects.feature.ai)
            implementation(projects.feature.voice)
            implementation(projects.core.viewmodel)
            implementation(libs.compose.material3)
            implementation(libs.compose.material.icons.extended)
            implementation(libs.androidx.lifecycle.viewmodel)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.kotlinx.io.core)
            implementation(libs.kotlinx.datetime)
            implementation(libs.koin.core)
            implementation(libs.koin.compose.viewmodel)
            implementation(libs.text.to.speech)
            implementation(libs.text.to.speech.compose)
        }

        androidMain.dependencies {
            implementation(libs.androidx.activity.compose)
        }

        wasmJsMain.dependencies {
            implementation(libs.kotlinx.browser)
        }

        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.kotlinx.coroutines.test)
            implementation(libs.turbine)
        }
    }
}

compose.resources {
    publicResClass = false
    packageOfResClass = "com.jarvis.chat.feature.chat.resources"
    generateResClass = always
}
