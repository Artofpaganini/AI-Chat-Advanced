package com.alva.scaffold

import java.io.File

// Результат сборки аггрегатного <Feature>Module.kt.
data class ModuleAssembleResult(
    val target: File?,
    val action: RenderAction?,
    // Строки-биндинги для ручной вставки, если файл уже существовал.
    val pendingBindings: List<String>,
    // true если файл был создан этим прогоном (нужно для шага 3 чеклиста).
    val createdNow: Boolean,
)

// Собирает <FeaturePascal>Module.kt из присутствующих биндингов.
// Имя файла/val выводятся из ФИЧИ (не из <Name> сабкоманды) — как в scaffold.sh.
// Биндинги внутри — по <Name>. Если файл уже есть — НЕ переписываем,
// возвращаем строки для ручной вставки в чеклист.
class ModuleAssembler(
    private val names: DerivedNames,
    private val moduleSrcRoot: File,
    private val force: Boolean,
    private val dryRun: Boolean,
) {

    private val featurePascal: String = NameDeriver.toPascalCase(names.feature)
    private val featureCamel: String = NameDeriver.toCamelCase(names.feature)

    fun assemble(hasData: Boolean, hasDomain: Boolean, hasPresentation: Boolean): ModuleAssembleResult {
        // Нет ни одного биндинга -> файл не нужен (тонкий nav-модуль).
        if (!hasData && !hasDomain && !hasPresentation) {
            return ModuleAssembleResult(target = null, action = null, pendingBindings = emptyList(), createdNow = false)
        }
        val target = File(moduleSrcRoot, "di/${featurePascal}Module.kt")
        // Существующий аггрегатный модуль не трогаем — отдаём строки для ручной вставки.
        if (target.exists() && !force) {
            // Печатаем pending только для биндингов, которых в существующем Module ещё нет —
            // иначе при повторном --full получался ложный hint «добавь …», хотя всё уже на месте.
            val existingContent = target.readText()
            val pending = buildList {
                if (hasData && !existingContent.contains("::${names.namePascal}RepositoryImpl")) {
                    add("// в ${featurePascal}Module.kt добавь: factoryOf(::${names.namePascal}RepositoryImpl) bind ${names.namePascal}Repository::class")
                }
                if (hasDomain && !existingContent.contains("::${names.namePascal}UseCase")) {
                    add("// в ${featurePascal}Module.kt добавь: factoryOf(::${names.namePascal}UseCase)")
                }
                if (hasPresentation && !existingContent.contains("::${names.namePascal}ViewModel")) {
                    add("// в ${featurePascal}Module.kt добавь: viewModelOf(::${names.namePascal}ViewModel)")
                }
            }
            return ModuleAssembleResult(
                target = target,
                action = RenderAction.SKIP,
                pendingBindings = pending,
                createdNow = false,
            )
        }
        val content = buildModuleContent(hasData = hasData, hasDomain = hasDomain, hasPresentation = hasPresentation)
        if (!dryRun) {
            target.parentFile?.mkdirs()
            target.writeText(content)
        }
        return ModuleAssembleResult(
            target = target,
            action = RenderAction.CREATE,
            pendingBindings = emptyList(),
            createdNow = true,
        )
    }

    private fun buildModuleContent(hasData: Boolean, hasDomain: Boolean, hasPresentation: Boolean): String {
        val pascal = names.namePascal
        val pkg = names.packageName
        val imports = buildList {
            if (hasData) {
                add("import $pkg.data.repository.${pascal}RepositoryImpl")
                add("import $pkg.domain.repository.${pascal}Repository")
            }
            if (hasDomain) {
                add("import $pkg.domain.usecase.${pascal}UseCase")
            }
            if (hasPresentation) {
                add("import $pkg.presentation.${pascal}ViewModel")
                add("import org.koin.core.annotation.KoinExperimentalAPI")
            }
            add("import org.koin.core.module.Module")
            if (hasData || hasDomain) {
                add("import org.koin.core.module.dsl.factoryOf")
            }
            if (hasPresentation) {
                add("import org.koin.core.module.dsl.viewModelOf")
            }
            if (hasData) {
                add("import org.koin.dsl.bind")
            }
            add("import org.koin.dsl.module")
        }
        val bindings = buildList {
            if (hasData) {
                add("    factoryOf(::${pascal}RepositoryImpl) bind ${pascal}Repository::class")
            }
            if (hasDomain) {
                add("    factoryOf(::${pascal}UseCase)")
            }
            if (hasPresentation) {
                add("    viewModelOf(::${pascal}ViewModel)")
            }
        }
        val optInLine = if (hasPresentation) "@OptIn(KoinExperimentalAPI::class)\n" else ""
        return buildString {
            append("package $pkg.di\n\n")
            append(imports.joinToString(separator = "\n"))
            append("\n\n")
            append(optInLine)
            append("val ${featureCamel}Module: Module = module {\n")
            append(bindings.joinToString(separator = "\n"))
            append("\n}\n")
        }
    }
}
