package com.alva.scaffold

// Результат деривации имён для одного модуля/класса.
// Зеркалит логику scaffold.sh: snake_case имя -> набор плейсхолдеров.
data class DerivedNames(
    val area: String,
    val feature: String,
    val packageName: String,
    val namePascal: String,
    val nameCamel: String,
)

object NameDeriver {

    private val featureNameRegex = Regex("^[a-z][a-z0-9_]*$")
    private val pascalNameRegex = Regex("^[A-Z][A-Za-z0-9]*$")

    // Валидация имени feature/core-модуля (snake_case).
    fun validateFeatureName(name: String) {
        if (!featureNameRegex.matches(name)) {
            error("недопустимое имя '$name': разрешён только snake_case [a-z][a-z0-9_]* (например, sleep_timer)")
        }
    }

    // Валидация PascalCase <Name>.
    fun validatePascalName(name: String) {
        if (!pascalNameRegex.matches(name)) {
            error("недопустимое имя '$name': требуется PascalCase [A-Z][A-Za-z0-9]* (например, SleepTimer)")
        }
    }

    // snake_case -> PascalCase. sleep_timer -> SleepTimer.
    fun toPascalCase(input: String): String =
        input.split("_")
            .filter { part -> part.isNotEmpty() }
            .joinToString(separator = "") { part -> part.replaceFirstChar { char -> char.uppercaseChar() } }

    // snake_case -> camelCase. sleep_timer -> sleepTimer.
    fun toCamelCase(input: String): String =
        toPascalCase(input).replaceFirstChar { char -> char.lowercaseChar() }

    // PascalCase -> camelCase. Extra -> extra.
    fun pascalToCamel(pascal: String): String =
        pascal.replaceFirstChar { char -> char.lowercaseChar() }

    // Деривация для feature/core-модуля по snake_case имени.
    fun deriveModule(area: String, name: String): DerivedNames {
        validateFeatureName(name)
        return DerivedNames(
            area = area,
            feature = name,
            packageName = "com.alva.$area.$name",
            namePascal = toPascalCase(name),
            nameCamel = toCamelCase(name),
        )
    }

    // Деривация для add-сабкоманд: <Name> (Pascal) внутри существующей feature.
    fun deriveInFeature(feature: String, pascal: String): DerivedNames {
        validateFeatureName(feature)
        validatePascalName(pascal)
        return DerivedNames(
            area = "feature",
            feature = feature,
            packageName = "com.alva.feature.$feature",
            namePascal = pascal,
            nameCamel = pascalToCamel(pascal),
        )
    }
}
