package com.alva.scaffold

import java.io.File

// Одно изменение общего файла (для лога и dry-run-диффа).
data class WireChange(
    val file: File,
    val addedLines: List<String>,
    val alreadyPresent: Boolean,
)

// Идемпотентно правит общие файлы проекта (settings.gradle.kts, NavigationsModule.kt,
// FeatureModule.kt). В dry-run только считает дифф, ничего не пишет.
class ProjectWirer(
    private val rootDir: File,
    private val names: DerivedNames,
    private val dryRun: Boolean,
) {

    private val featureCamel: String = NameDeriver.toCamelCase(names.feature)

    private val settingsFile: File = File(rootDir, "settings.gradle.kts")
    private val navigationsModuleFile: File =
        File(rootDir, "composeApp/src/commonMain/kotlin/com/alva/di/NavigationsModule.kt")
    private val featureModuleFile: File =
        File(rootDir, "composeApp/src/commonMain/kotlin/com/alva/di/FeatureModule.kt")

    // Добавить include(":<area>:<name>") в settings.gradle.kts.
    // wireNav: вписать <name>NavigationModule в NavigationsModule.kt.
    // wireFeatureModule: вписать <name>Module в FeatureModule.kt.
    fun wire(wireNav: Boolean, wireFeatureModule: Boolean): List<WireChange> {
        val changes = mutableListOf<WireChange>()
        changes.add(wireSettings())
        if (wireNav) {
            changes.add(wireNavigationsModule())
        }
        if (wireFeatureModule) {
            changes.add(wireFeatureModule())
        }
        return changes
    }

    private fun wireSettings(): WireChange {
        val includeLine = "include(\":${names.area}:${names.feature}\")"
        val text = settingsFile.readText()
        if (text.lineSequence().any { line -> line.trim() == includeLine }) {
            return WireChange(file = settingsFile, addedLines = listOf(includeLine), alreadyPresent = true)
        }
        val sectionMarker = when (names.area) {
            "core" -> "// Core modules"
            else -> "// Feature modules"
        }
        val lines = text.lines().toMutableList()
        val insertionIndex = computeIncludeInsertionIndex(lines = lines, sectionMarker = sectionMarker)
        lines.add(insertionIndex, includeLine)
        if (!dryRun) {
            settingsFile.writeText(lines.joinToString(separator = "\n"))
        }
        return WireChange(file = settingsFile, addedLines = listOf(includeLine), alreadyPresent = false)
    }

    // Вставка после последнего include в секции; если секции нет — после последнего include файла.
    private fun computeIncludeInsertionIndex(lines: List<String>, sectionMarker: String): Int {
        val sectionStart = lines.indexOfFirst { line -> line.trim() == sectionMarker }
        val searchFrom = if (sectionStart >= 0) sectionStart + 1 else 0
        var lastInclude = -1
        for (index in searchFrom until lines.size) {
            val trimmed = lines[index].trim()
            // Останавливаемся на следующей секции-комментарии при найденном блоке.
            if (sectionStart >= 0 && lastInclude >= 0 && trimmed.startsWith("//")) {
                break
            }
            if (trimmed.startsWith("include(")) {
                lastInclude = index
            }
        }
        return if (lastInclude >= 0) lastInclude + 1 else lines.size
    }

    private fun wireNavigationsModule(): WireChange =
        wireDiAggregator(
            file = navigationsModuleFile,
            importLine = "import ${names.packageName}.di.${featureCamel}NavigationModule",
            includeEntry = "${featureCamel}NavigationModule",
        )

    private fun wireFeatureModule(): WireChange =
        wireDiAggregator(
            file = featureModuleFile,
            importLine = "import ${names.packageName}.di.${featureCamel}Module",
            includeEntry = "${featureCamel}Module",
        )

    // Идемпотентно добавляет import рядом с существующими и запись в includes(...).
    private fun wireDiAggregator(file: File, importLine: String, includeEntry: String): WireChange {
        val text = file.readText()
        val lines = text.lines().toMutableList()
        val importPresent = lines.any { line -> line.trim() == importLine }
        val entryPresent = lines.any { line -> line.trim().removeSuffix(",") == includeEntry }
        if (importPresent && entryPresent) {
            return WireChange(file = file, addedLines = listOf(importLine, "$includeEntry,"), alreadyPresent = true)
        }
        val added = mutableListOf<String>()
        if (!importPresent) {
            insertImport(lines = lines, importLine = importLine)
            added.add(importLine)
        }
        if (!entryPresent) {
            insertIncludeEntry(lines = lines, includeEntry = includeEntry)
            added.add("$includeEntry,")
        }
        if (!dryRun) {
            file.writeText(lines.joinToString(separator = "\n"))
        }
        return WireChange(file = file, addedLines = added, alreadyPresent = false)
    }

    // Импорт вставляется в отсортированную позицию (ktlint import-ordering): перед первым
    // существующим import, лексикографически большим нового. Fallback — после последнего
    // import либо после строки package.
    private fun insertImport(lines: MutableList<String>, importLine: String) {
        val importIndices = lines.indices.filter { index -> lines[index].trim().startsWith("import ") }
        val greaterIndex = importIndices.firstOrNull { index -> lines[index].trim() > importLine }
        val insertionIndex = when {
            greaterIndex != null -> greaterIndex
            importIndices.isNotEmpty() -> importIndices.last() + 1
            else -> packageInsertionIndex(lines)
        }
        lines.add(insertionIndex, importLine)
    }

    // Индекс вставки при отсутствии import: после строки package (с пустой строкой), иначе в начало.
    private fun packageInsertionIndex(lines: List<String>): Int {
        val packageIndex = lines.indexOfFirst { line -> line.trim().startsWith("package ") }
        return if (packageIndex >= 0) packageIndex + 1 else 0
    }

    // Запись добавляется как последний элемент includes(...): к предыдущему последнему
    // элементу дописываем запятую (если её нет), новую запись — без запятой.
    private fun insertIncludeEntry(lines: MutableList<String>, includeEntry: String) {
        val includesStart = lines.indexOfFirst { line -> line.contains("includes(") }
        if (includesStart < 0) {
            error("в файле не найден блок includes(...) — авто-вайринг невозможен")
        }
        val closingIndex = findIncludesClosingIndex(lines = lines, includesStart = includesStart)
        val lastEntryIndex = findLastEntryIndex(lines = lines, includesStart = includesStart, closingIndex = closingIndex)
        if (lastEntryIndex >= 0) {
            val lastEntry = lines[lastEntryIndex]
            if (!lastEntry.trimEnd().endsWith(",")) {
                lines[lastEntryIndex] = lastEntry.trimEnd() + ","
            }
        }
        val indent = detectEntryIndent(lines = lines, lastEntryIndex = lastEntryIndex, includesStart = includesStart)
        lines.add(closingIndex, "$indent$includeEntry")
    }

    private fun findIncludesClosingIndex(lines: List<String>, includesStart: Int): Int {
        for (index in includesStart until lines.size) {
            if (lines[index].trim().startsWith(")")) {
                return index
            }
        }
        error("не найдена закрывающая скобка includes(...)")
    }

    private fun findLastEntryIndex(lines: List<String>, includesStart: Int, closingIndex: Int): Int {
        for (index in (closingIndex - 1) downTo (includesStart + 1)) {
            val trimmed = lines[index].trim()
            if (trimmed.isNotEmpty() && !trimmed.startsWith("//")) {
                return index
            }
        }
        return -1
    }

    private fun detectEntryIndent(lines: List<String>, lastEntryIndex: Int, includesStart: Int): String {
        val sample = if (lastEntryIndex >= 0) lines[lastEntryIndex] else lines[includesStart]
        val indentLength = sample.takeWhile { char -> char == ' ' }.length
        val effective = if (lastEntryIndex >= 0) indentLength else indentLength + 4
        return " ".repeat(effective)
    }
}
