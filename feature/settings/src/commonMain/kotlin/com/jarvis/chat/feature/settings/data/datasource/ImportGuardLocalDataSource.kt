package com.jarvis.chat.feature.settings.data.datasource

internal interface ImportGuardLocalDataSource {

    fun getImportGuardEnabled(): Boolean?

    fun saveImportGuardEnabled(enabled: Boolean)
}
