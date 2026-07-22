package com.alva

import com.alva.scaffold.tasks.NewComponentTask
import com.alva.scaffold.tasks.NewCoreTask
import com.alva.scaffold.tasks.NewFeatureTask
import com.alva.scaffold.tasks.NewModelTask
import com.alva.scaffold.tasks.NewRepositoryTask
import com.alva.scaffold.tasks.NewScreenTask
import com.alva.scaffold.tasks.NewUseCaseTask
import com.alva.scaffold.tasks.NewViewModelTask
import com.alva.scaffold.tasks.ScaffoldTask

// Группа всех скаффолд-тасков в выводе ./gradlew tasks.
val scaffoldGroup = "Alva Scaffolding"

// Корень проекта резолвится здесь, на configuration-фазе, и хранится в задаче —
// чтобы @TaskAction не обращался к Task.project (несовместимо с configuration cache).
val projectRootDirectory = layout.projectDirectory

tasks.withType<ScaffoldTask>().configureEach {
    rootDirectory.set(projectRootDirectory)
}

tasks.register<NewFeatureTask>("feature") {
    group = scaffoldGroup
    description = "Создаёт feature-модуль (--name, --full/--layers/--no-*/--with-viewmodel, --preview)"
}

tasks.register<NewCoreTask>("core") {
    group = scaffoldGroup
    description = "Создаёт core-модуль (--name, --ui, --preview)"
}

tasks.register<NewViewModelTask>("viewModel") {
    group = scaffoldGroup
    description = "Добавляет UDF-комплект в feature (--name, --feature, --preview)"
}

tasks.register<NewUseCaseTask>("useCase") {
    group = scaffoldGroup
    description = "Добавляет UseCase в feature (--name, --feature, --preview)"
}

tasks.register<NewRepositoryTask>("repository") {
    group = scaffoldGroup
    description = "Добавляет Repository + Impl в feature (--name, --feature, --preview)"
}

tasks.register<NewScreenTask>("screen") {
    group = scaffoldGroup
    description = "Добавляет Compose-экран без ViewModel (--name, --feature, --preview)"
}

tasks.register<NewComponentTask>("component") {
    group = scaffoldGroup
    description = "Добавляет переиспользуемый Composable-компонент (--name, --feature, --preview)"
}

tasks.register<NewModelTask>("model") {
    group = scaffoldGroup
    description = "Добавляет модель domain/data + mapper (--name, --feature, --domain-only/--data-only, --preview)"
}
