package com.jarvis.chat.feature.settings.data.datasource

import com.russhwolf.settings.Settings

private const val KEY_IMPORT_GUARD = "import_guard_enabled"
private const val IMPORT_GUARD_DEFAULT_ENABLED = true

internal class ImportGuardLocalDataSourceImpl(
    private val settings: Settings,
) : ImportGuardLocalDataSource {

    override fun getImportGuardEnabled(): Boolean? =
        if (settings.hasKey(KEY_IMPORT_GUARD)) {
            settings.getBoolean(KEY_IMPORT_GUARD, IMPORT_GUARD_DEFAULT_ENABLED)
        } else {
            null
        }

    override fun saveImportGuardEnabled(enabled: Boolean) {
        settings.putBoolean(KEY_IMPORT_GUARD, enabled)
    }
}
