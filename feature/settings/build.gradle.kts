plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.feature.settings"
        withHostTest {}
    }

    sourceSets {
        commonMain.dependencies {
            implementation(projects.core.viewmodel)
            implementation(libs.compose.material3)
            implementation(libs.androidx.lifecycle.viewmodel)
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.koin.core)
            implementation(libs.koin.compose.viewmodel)
            implementation(libs.multiplatform.settings)
            implementation(libs.multiplatform.settings.no.arg)
        }

        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.kotlinx.coroutines.test)
            implementation(libs.turbine)
        }
    }
}
