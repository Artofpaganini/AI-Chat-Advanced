package com.alva

import com.alva.utils.applyIfNeeded
import com.alva.utils.libs
import com.alva.utils.sourceExcludeGlobs
import org.gradle.api.attributes.Bundling

plugins.applyIfNeeded("java")

private val ktLintConfig = configurations.create("ktlint")

dependencies {
    "ktlint"(libs.classpath.ktlint.cli) {
        attributes {
            attribute(
                Bundling.BUNDLING_ATTRIBUTE,
                objects.named<Bundling>(Bundling.EXTERNAL)
            )
        }
    }
}

// Ktlint ожидает паттерны с префиксом `!` для exclude и без префикса для include.
// Преобразуем общие excludes из `sourceExcludeGlobs` в ktlint-формат и добавляем
// корневой include `**/src/**/*.kt`.
private val sources: List<String> = sourceExcludeGlobs.map { excludeGlob -> "!$excludeGlob" } +
    "**/src/**/*.kt"

// ktlint doesn't support disabling filename rule via CLI args
// Instead, we exclude problematic files in sources list
private val ktlintArgs = emptyList<String>()

private val reportsDirPath = project.layout.buildDirectory.dir("reports/ktlint").get().asFile.path
private val ktLintCliMainClass = "com.pinterest.ktlint.Main"
private val reportArgs = listOf(
    "--reporter=plain",
    "--reporter=checkstyle,output=$reportsDirPath/ktlint.xml",
    "--reporter=html,output=$reportsDirPath/ktlint.html",
)

val ktLintCheckTask = tasks.register<JavaExec>("ktlintCheck") {
    group = "verification"
    description = "Check Kotlin code style."
    classpath = ktLintConfig
    mainClass = ktLintCliMainClass
    // Режим pre-push: проверяем только изменённые файлы
    val changedFilesProperty = project.findProperty("changedFiles") as? String
    val inputSources: List<String> = changedFilesProperty?.split(",")?.filter { it.endsWith(".kt") } ?: sources
    args = ktlintArgs + reportArgs + inputSources
}

tasks.named("check") {
    dependsOn(ktLintCheckTask)
}

tasks.register<JavaExec>("ktlintFormat") {
    group = "formatting"
    description = "Fix Kotlin code style deviations."
    classpath = ktLintConfig
    mainClass = ktLintCliMainClass
    jvmArgs = listOf("--add-opens=java.base/java.lang=ALL-UNNAMED")
    // Режим pre-push: форматируем только изменённые файлы
    val changedFilesProperty = project.findProperty("changedFiles") as? String
    val inputSources: List<String> = changedFilesProperty?.split(",")?.filter { it.endsWith(".kt") } ?: sources
    args = ktlintArgs + listOf("-F") + inputSources
}

