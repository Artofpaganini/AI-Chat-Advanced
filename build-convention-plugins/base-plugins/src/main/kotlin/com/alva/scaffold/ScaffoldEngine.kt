package com.alva.scaffold

import java.io.File

// Набор слоёв feature-модуля.
data class FeatureLayers(
    val nav: Boolean,
    val presentation: Boolean,
    val domain: Boolean,
    val data: Boolean,
) {
    val hasAnyBinding: Boolean get() = data || domain || presentation
}

// Движок: оркестрирует рендер шаблонов, сборку di-модуля, авто-вайринг
// и сбор вывода (включая dry-run-дифф). Не зависит от Gradle API.
@Suppress("TooManyFunctions")
class ScaffoldEngine(
    private val rootDir: File,
    private val force: Boolean,
    private val dryRun: Boolean,
) {

    private val templatesDir: File = File(rootDir, "scripts/templates")
    private val output: StringBuilder = StringBuilder()

    val report: String get() = output.toString()

    private fun moduleRoot(names: DerivedNames): File =
        File(rootDir, "${names.area}/${names.feature}")

    private fun moduleSrcRoot(names: DerivedNames): File =
        File(moduleRoot(names), "src/commonMain/kotlin/com/alva/${names.area}/${names.feature}")

    private fun renderer(names: DerivedNames): TemplateRenderer =
        TemplateRenderer(templatesDir = templatesDir, names = names, force = force, dryRun = dryRun)

    // --- feature ---
    fun feature(name: String, layers: FeatureLayers) {
        val names = NameDeriver.deriveModule(area = "feature", name = name)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("feature: ${names.feature} (package ${names.packageName})")
        line(
            "layers: nav=${layers.nav.bit} presentation=${layers.presentation.bit} " +
                "domain=${layers.domain.bit} data=${layers.data.bit}",
        )
        blank()
        renderer.render("feature/build.gradle.kts.template", File(moduleRoot(names), "build.gradle.kts"))
        if (layers.nav) {
            renderNavLayer(renderer = renderer, src = src, names = names)
        }
        if (layers.presentation) {
            renderPresentationLayer(renderer = renderer, src = src, names = names)
        }
        if (layers.domain) {
            renderDomainLayer(renderer = renderer, src = src, names = names)
        }
        if (layers.data) {
            renderDataLayer(renderer = renderer, src = src, names = names)
        }
        if (layers.nav && !layers.presentation) {
            renderer.render(
                "feature/presentation/{{NAME}}Screen.thin.kt.template",
                File(src, "presentation/${names.namePascal}Screen.kt"),
            )
        }
        logRenders(renderer.results)
        val moduleResult = ModuleAssembler(
            names = names,
            moduleSrcRoot = src,
            force = force,
            dryRun = dryRun,
        ).assemble(hasData = layers.data, hasDomain = layers.domain, hasPresentation = layers.presentation)
        logModuleResult(moduleResult)
        wireAndReport(
            names = names,
            wireNav = layers.nav,
            wireFeatureModule = moduleResult.createdNow,
            pendingBindings = moduleResult.pendingBindings,
        )
        warnIncompleteChain(names = names, layers = layers)
    }

    // --- core ---
    fun core(name: String, withUi: Boolean) {
        val names = NameDeriver.deriveModule(area = "core", name = name)
        val renderer = renderer(names)
        line("core: ${names.feature} (package ${names.packageName}, ui=${withUi.bit})")
        blank()
        val buildTemplate = if (withUi) {
            "core/build.gradle.ui.kts.template"
        } else {
            "core/build.gradle.kts.template"
        }
        renderer.render(buildTemplate, File(moduleRoot(names), "build.gradle.kts"))
        val gitkeep = File(moduleSrcRoot(names), ".gitkeep")
        renderGitkeep(gitkeep)
        logRenders(renderer.results)
        wireAndReport(names = names, wireNav = false, wireFeatureModule = false, pendingBindings = emptyList())
    }

    // --- viewmodel ---
    fun viewModel(pascal: String, feature: String) {
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("viewmodel: ${names.namePascal} в feature ${names.feature}")
        blank()
        val featurePascal = NameDeriver.toPascalCase(names.feature)
        val moduleExisted = File(src, "di/${featurePascal}Module.kt").exists()
        val screenFile = File(src, "presentation/${names.namePascal}Screen.kt")
        if (screenFile.exists() && !force) {
            line("warn:  Screen уже существует — будет skip. Для перезаписи заглушки на UDF используй --force.")
        }
        renderPresentationLayer(renderer = renderer, src = src, names = names)
        logRenders(renderer.results)
        val moduleResult = ModuleAssembler(names = names, moduleSrcRoot = src, force = force, dryRun = dryRun)
            .assemble(hasData = false, hasDomain = false, hasPresentation = true)
        logModuleResult(moduleResult)
        wireAndReport(
            names = names,
            wireNav = false,
            wireFeatureModule = !moduleExisted && moduleResult.createdNow,
            pendingBindings = moduleResult.pendingBindings,
        )
    }

    // --- usecase ---
    fun useCase(pascal: String, feature: String) {
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("usecase: ${names.namePascal}UseCase в feature ${names.feature}")
        blank()
        val featurePascal = NameDeriver.toPascalCase(names.feature)
        val moduleExisted = File(src, "di/${featurePascal}Module.kt").exists()
        renderer.render(
            "usecase/{{NAME}}UseCase.kt.template",
            File(src, "domain/usecase/${names.namePascal}UseCase.kt"),
        )
        logRenders(renderer.results)
        val moduleResult = ModuleAssembler(names = names, moduleSrcRoot = src, force = force, dryRun = dryRun)
            .assemble(hasData = false, hasDomain = true, hasPresentation = false)
        logModuleResult(moduleResult)
        wireAndReport(
            names = names,
            wireNav = false,
            wireFeatureModule = !moduleExisted && moduleResult.createdNow,
            pendingBindings = moduleResult.pendingBindings,
        )
    }

    // --- repository ---
    fun repository(pascal: String, feature: String) {
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("repository: ${names.namePascal}Repository (+Impl) в feature ${names.feature}")
        blank()
        val featurePascal = NameDeriver.toPascalCase(names.feature)
        val moduleExisted = File(src, "di/${featurePascal}Module.kt").exists()
        renderer.render(
            "repository/{{NAME}}Repository.kt.template",
            File(src, "domain/repository/${names.namePascal}Repository.kt"),
        )
        renderer.render(
            "repository/{{NAME}}RepositoryImpl.kt.template",
            File(src, "data/repository/${names.namePascal}RepositoryImpl.kt"),
        )
        logRenders(renderer.results)
        val moduleResult = ModuleAssembler(names = names, moduleSrcRoot = src, force = force, dryRun = dryRun)
            .assemble(hasData = true, hasDomain = false, hasPresentation = false)
        logModuleResult(moduleResult)
        wireAndReport(
            names = names,
            wireNav = false,
            wireFeatureModule = !moduleExisted && moduleResult.createdNow,
            pendingBindings = moduleResult.pendingBindings,
        )
    }

    // --- model ---
    fun model(pascal: String, feature: String, domainOnly: Boolean, dataOnly: Boolean) {
        if (domainOnly && dataOnly) {
            error("--domain-only и --data-only взаимоисключающие")
        }
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line(
            "model: ${names.namePascal} в feature ${names.feature} " +
                "(domain-only=${domainOnly.bit} data-only=${dataOnly.bit})",
        )
        blank()
        if (!dataOnly) {
            renderer.render(
                "model/{{NAME}}Model.kt.template",
                File(src, "domain/model/${names.namePascal}Model.kt"),
            )
        }
        if (!domainOnly) {
            renderer.render(
                "model/{{NAME}}DataModel.kt.template",
                File(src, "data/model/${names.namePascal}DataModel.kt"),
            )
            renderer.render(
                "model/{{NAME}}DataModelMapper.kt.template",
                File(src, "data/mapper/${names.namePascal}DataModelMapper.kt"),
            )
        }
        logRenders(renderer.results)
    }

    // --- screen ---
    fun screen(pascal: String, feature: String) {
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("screen: ${names.namePascal}Screen в feature ${names.feature}")
        blank()
        renderer.render(
            "compose/{{NAME}}Screen.kt.template",
            File(src, "presentation/${names.namePascal}Screen.kt"),
        )
        logRenders(renderer.results)
    }

    // --- component ---
    fun component(pascal: String, feature: String) {
        val names = requireFeature(feature = feature, pascal = pascal)
        val src = moduleSrcRoot(names)
        val renderer = renderer(names)
        line("component: ${names.namePascal} в feature ${names.feature}")
        blank()
        renderer.render(
            "compose/{{NAME}}Component.kt.template",
            File(src, "presentation/component/${names.namePascal}.kt"),
        )
        logRenders(renderer.results)
    }

    // --- общие хелперы рендера слоёв ---
    private fun renderNavLayer(renderer: TemplateRenderer, src: File, names: DerivedNames) {
        renderer.render(
            "feature/di/{{NAME}}NavigationModule.kt.template",
            File(src, "di/${names.namePascal}NavigationModule.kt"),
        )
        renderer.render(
            "feature/presentation/route/{{NAME}}Route.kt.template",
            File(src, "presentation/route/${names.namePascal}Route.kt"),
        )
    }

    private fun renderPresentationLayer(renderer: TemplateRenderer, src: File, names: DerivedNames) {
        val pascal = names.namePascal
        renderer.render("viewmodel/presentation/{{NAME}}ViewModel.kt.template", File(src, "presentation/${pascal}ViewModel.kt"))
        renderer.render("viewmodel/presentation/{{NAME}}Screen.udf.kt.template", File(src, "presentation/${pascal}Screen.kt"))
        renderer.render("viewmodel/presentation/model/{{NAME}}State.kt.template", File(src, "presentation/model/${pascal}State.kt"))
        renderer.render("viewmodel/presentation/model/{{NAME}}Action.kt.template", File(src, "presentation/model/${pascal}Action.kt"))
        renderer.render("viewmodel/presentation/model/{{NAME}}Event.kt.template", File(src, "presentation/model/${pascal}Event.kt"))
        renderer.render("viewmodel/presentation/model/{{NAME}}UiState.kt.template", File(src, "presentation/model/${pascal}UiState.kt"))
        renderer.render("viewmodel/presentation/mapper/{{NAME}}UiStateMapper.kt.template", File(src, "presentation/mapper/${pascal}UiStateMapper.kt"))
    }

    private fun renderDomainLayer(renderer: TemplateRenderer, src: File, names: DerivedNames) {
        val pascal = names.namePascal
        renderer.render("model/{{NAME}}Model.kt.template", File(src, "domain/model/${pascal}Model.kt"))
        renderer.render("repository/{{NAME}}Repository.kt.template", File(src, "domain/repository/${pascal}Repository.kt"))
        renderer.render("usecase/{{NAME}}UseCase.kt.template", File(src, "domain/usecase/${pascal}UseCase.kt"))
    }

    private fun renderDataLayer(renderer: TemplateRenderer, src: File, names: DerivedNames) {
        val pascal = names.namePascal
        renderer.render("model/{{NAME}}DataModel.kt.template", File(src, "data/model/${pascal}DataModel.kt"))
        renderer.render("model/{{NAME}}DataModelMapper.kt.template", File(src, "data/mapper/${pascal}DataModelMapper.kt"))
        renderer.render("repository/{{NAME}}RepositoryImpl.kt.template", File(src, "data/repository/${pascal}RepositoryImpl.kt"))
    }

    private fun renderGitkeep(gitkeep: File) {
        if (gitkeep.exists() && !force) {
            line("skip   ${relative(gitkeep)}")
            return
        }
        if (!dryRun) {
            gitkeep.parentFile?.mkdirs()
            gitkeep.writeText("")
        }
        line("create ${relative(gitkeep)}")
    }

    private fun requireFeature(feature: String, pascal: String): DerivedNames {
        NameDeriver.validateFeatureName(feature)
        val moduleDir = File(rootDir, "feature/$feature")
        if (!moduleDir.isDirectory) {
            if (File(rootDir, "core/$feature").isDirectory) {
                error("'$feature' — core-модуль; presentation/domain/data-сабкоманды доступны только для feature")
            }
            error("feature '$feature' не найден (${moduleDir.absolutePath}). Сначала создай: feature --name=$feature")
        }
        return NameDeriver.deriveInFeature(feature = feature, pascal = pascal)
    }

    // --- авто-вайринг + чеклист ---
    private fun wireAndReport(
        names: DerivedNames,
        wireNav: Boolean,
        wireFeatureModule: Boolean,
        pendingBindings: List<String>,
    ) {
        val wirer = ProjectWirer(rootDir = rootDir, names = names, dryRun = dryRun)
        val changes = wirer.wire(wireNav = wireNav, wireFeatureModule = wireFeatureModule)
        blank()
        val header = if (dryRun) {
            "--- DRY-RUN: авто-вайринг (дифф, файлы НЕ изменяются) ---"
        } else {
            "--- Авто-вайринг (общие файлы обновлены идемпотентно) ---"
        }
        line(header)
        changes.forEach { change -> reportChange(change) }
        if (pendingBindings.isNotEmpty()) {
            line("Биндинги для ручной вставки (аггрегатный Module.kt уже существует, не трогаем):")
            pendingBindings.forEach { binding -> line(binding) }
        }
    }

    private fun reportChange(change: WireChange) {
        val path = relative(change.file)
        if (change.alreadyPresent) {
            line("no-op  $path (уже подключено)")
            return
        }
        val verb = if (dryRun) "would edit" else "edited "
        line("$verb $path")
        change.addedLines.forEach { added -> line("    + $added") }
    }

    private fun warnIncompleteChain(names: DerivedNames, layers: FeatureLayers) {
        if (layers.domain && !layers.data) {
            line("⚠ слой data отсутствует — ${names.namePascal}Repository нужно реализовать и забиндить вручную")
        }
        if (layers.presentation && !layers.domain) {
            line("примечание: слой domain отсутствует — UseCase не подключён к ViewModel")
        }
    }

    private fun logRenders(results: List<RenderResult>) {
        results.forEach { result ->
            val verb = when (result.action) {
                RenderAction.CREATE -> "create"
                RenderAction.SKIP -> "skip  "
            }
            line("$verb ${relative(result.target)}")
        }
    }

    private fun logModuleResult(result: ModuleAssembleResult) {
        val target = result.target ?: return
        val verb = when (result.action) {
            RenderAction.CREATE -> "create"
            RenderAction.SKIP -> "skip  "
            null -> return
        }
        line("$verb ${relative(target)}")
    }

    private fun relative(file: File): String =
        file.absoluteFile.relativeToOrSelf(rootDir.absoluteFile).path

    private fun line(text: String) {
        output.append(text).append('\n')
    }

    private fun blank() {
        output.append('\n')
    }

    private val Boolean.bit: Int get() = if (this) 1 else 0
}
