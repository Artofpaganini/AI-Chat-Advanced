plugins {
    alias(libs.plugins.internal.kmp.setup)
    alias(libs.plugins.internal.cmp.setup)
    alias(libs.plugins.kotlinx.serialization)
}

kotlin {
    android {
        namespace = "com.jarvis.chat.core.micromodel"
        withHostTest {}
    }

    sourceSets {
        commonMain.dependencies {
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
            implementation(libs.koin.core)
        }

        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.kotlinx.coroutines.test)
            implementation(libs.kotlinx.io.core)
        }
    }
}

compose.resources {
    publicResClass = false
    packageOfResClass = "com.jarvis.chat.core.micromodel.resources"
    generateResClass = always
}

tasks.withType<Test>().configureEach {
    workingDir = rootProject.projectDir
}

val microModelWeightsSourceFile = rootProject.file("challenge_advanced/task10/results/micro_model.json")
val microModelWeightsResourceFile = layout.projectDirectory.file("src/commonMain/composeResources/files/micro_model.json").asFile

tasks.register<Copy>("syncMicroModelWeights") {
    from(microModelWeightsSourceFile)
    into(microModelWeightsResourceFile.parentFile)
    rename { microModelWeightsResourceFile.name }
}

tasks.register("verifyMicroModelWeightsSynced") {
    doLast {
        if (!microModelWeightsSourceFile.exists()) {
            println(
                "SKIPPED: источник весов $microModelWeightsSourceFile не найден в этом чекауте - " +
                    "проверка синхронизации пропущена, это не ошибка.",
            )
            return@doLast
        }
        check(microModelWeightsResourceFile.exists()) {
            "Источник весов есть, но копия в ресурсах отсутствует: $microModelWeightsResourceFile. " +
                "Запустите ./gradlew :core:micromodel:syncMicroModelWeights"
        }
        check(microModelWeightsSourceFile.readBytes().contentEquals(microModelWeightsResourceFile.readBytes())) {
            "$microModelWeightsResourceFile разошёлся с $microModelWeightsSourceFile. " +
                "Запустите ./gradlew :core:micromodel:syncMicroModelWeights"
        }
    }
}
