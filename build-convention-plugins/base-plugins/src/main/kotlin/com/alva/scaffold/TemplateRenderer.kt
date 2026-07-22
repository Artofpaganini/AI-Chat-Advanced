package com.alva.scaffold

import java.io.File

// Результат рендера одного файла (для лога и dry-run).
data class RenderResult(
    val target: File,
    val action: RenderAction,
)

enum class RenderAction {
    CREATE,
    SKIP,
}

// Рендерит .template из <rootDir>/scripts/templates/, подставляя плейсхолдеры
// обычным string replace (не sed). Пишет в целевой путь модуля.
// Идемпотентность: существующий файл -> skip (без force). В dry-run ничего не пишет.
class TemplateRenderer(
    private val templatesDir: File,
    private val names: DerivedNames,
    private val force: Boolean,
    private val dryRun: Boolean,
) {

    private val collectedResults: MutableList<RenderResult> = mutableListOf()

    val results: List<RenderResult> get() = collectedResults

    // Рендер одного шаблона. relativeTemplatePath — путь от templatesDir
    // (с плейсхолдером {{NAME}} в имени файла, который заменяется на PascalCase).
    fun render(relativeTemplatePath: String, target: File): RenderResult {
        val template = File(templatesDir, relativeTemplatePath)
        if (!template.exists()) {
            error("шаблон не найден: ${template.absolutePath}")
        }
        // Существующий файл не перезаписываем без force.
        if (target.exists() && !force) {
            return record(target, RenderAction.SKIP)
        }
        if (!dryRun) {
            target.parentFile?.mkdirs()
            target.writeText(substitute(template.readText()))
        }
        return record(target, RenderAction.CREATE)
    }

    // Подстановка плейсхолдеров. Порядок не критичен: ключи не пересекаются как подстроки
    // друг друга, кроме {{NAME}} / {{name}} — они различаются регистром и заменяются точно.
    private fun substitute(content: String): String =
        content
            .replace("{{PACKAGE}}", names.packageName)
            .replace("{{AREA}}", names.area)
            .replace("{{FEATURE}}", names.feature)
            .replace("{{NAME}}", names.namePascal)
            .replace("{{name}}", names.nameCamel)

    private fun record(target: File, action: RenderAction): RenderResult {
        val result = RenderResult(target = target, action = action)
        collectedResults.add(result)
        return result
    }
}
