import java.util.Properties
import org.jetbrains.kotlin.gradle.targets.js.webpack.KotlinWebpackConfig

plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
}

val localProperties = Properties().apply {
    val localPropertiesFile = rootProject.file("local.properties")
    if (localPropertiesFile.exists()) {
        localPropertiesFile.inputStream().use { stream -> load(stream) }
    }
}
val deepSeekApiKey: String = localProperties.getProperty("DEEPSEEK_API_KEY").orEmpty()

val generatedWebConfigDir = layout.buildDirectory.dir("generated/jarvisWebConfig/kotlin")
val generateJarvisWebConfig = tasks.register("generateJarvisWebConfig") {
    val outputDir = generatedWebConfigDir
    val apiKeyValue = deepSeekApiKey
    outputs.dir(outputDir)
    doLast {
        val packageDir = outputDir.get().dir("com/jarvis/chat").asFile
        packageDir.mkdirs()
        val escapedApiKey = apiKeyValue.replace("\\", "\\\\").replace("\"", "\\\"")
        packageDir.resolve("JarvisWebConfig.kt").writeText(
            """
            |package com.jarvis.chat
            |
            |internal object JarvisWebConfig {
            |    const val DEEPSEEK_API_KEY: String = "$escapedApiKey"
            |}
            |
            """.trimMargin(),
        )
    }
}

kotlin {
    android {
        namespace = "com.jarvis.chat"
    }

    listOf(
        iosArm64(),
        iosSimulatorArm64(),
    ).forEach { target ->
        target.binaries.framework {
            baseName = "JarvisApp"
            isStatic = true
        }
    }

    wasmJs {
        binaries.executable()
        browser {
            commonWebpackConfig {
                devServer = (devServer ?: KotlinWebpackConfig.DevServer()).apply {
                    proxy = (proxy ?: mutableListOf()).apply {
                        add(
                            KotlinWebpackConfig.DevServer.Proxy(
                                context = mutableListOf("/chat"),
                                target = "https://api.deepseek.com",
                                changeOrigin = true,
                                secure = false,
                            ),
                        )
                    }
                }
            }
        }
    }

    sourceSets {
        commonMain.dependencies {
            implementation(projects.feature.chat)
            implementation(libs.compose.material3)
            implementation(libs.koin.core)
        }

        wasmJsMain {
            kotlin.srcDir(generateJarvisWebConfig)
            dependencies {
                implementation(libs.kotlinx.browser)
            }
        }
    }
}
