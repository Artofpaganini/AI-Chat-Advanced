package com.jarvis.chat.feature.loopgenerated

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

internal class TokenStorage(context: Context) {

    private val preferences: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        PREFERENCE_FILE_NAME,
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun saveToken(token: String) {
        preferences.edit().putString(KEY_AUTH_TOKEN, token).apply()
    }

    fun getToken(): String? =
        preferences.getString(KEY_AUTH_TOKEN, null)

    private companion object {
        const val PREFERENCE_FILE_NAME = "secure_auth_preferences"
        const val KEY_AUTH_TOKEN = "auth_token"
    }
}
