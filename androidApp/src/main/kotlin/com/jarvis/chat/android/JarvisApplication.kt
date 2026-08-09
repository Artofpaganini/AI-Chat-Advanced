package com.jarvis.chat.android

import android.app.Application
import com.jarvis.chat.AppConfig
import com.jarvis.chat.di.initKoin

class JarvisApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        appConfig = AppConfig(
            deepSeekApiKey = BuildConfig.DEEPSEEK_API_KEY,
            deepSeekBaseUrl = DEEPSEEK_BASE_URL,
            filesDirectoryPath = filesDir.absolutePath,
            localModelBaseUrl = BuildConfig.LOCAL_MODEL_BASE_URL,
            triageBaseUrl = BuildConfig.TRIAGE_BASE_URL,
            gatewayBaseUrl = BuildConfig.GATEWAY_BASE_URL,
            codeLoopBaseUrl = BuildConfig.CODE_LOOP_BASE_URL,
        )
        initKoin(appConfig)
    }

    companion object {
        private const val DEEPSEEK_BASE_URL = "https://api.deepseek.com/"

        lateinit var appConfig: AppConfig
            private set
    }
}
