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
        )
        initKoin(appConfig)
    }

    companion object {
        private const val DEEPSEEK_BASE_URL = "https://api.deepseek.com/"

        lateinit var appConfig: AppConfig
            private set
    }
}
