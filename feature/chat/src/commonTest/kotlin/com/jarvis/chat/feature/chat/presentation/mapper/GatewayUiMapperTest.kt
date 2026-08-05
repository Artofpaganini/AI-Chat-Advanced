package com.jarvis.chat.feature.chat.presentation.mapper

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotEquals

private val KNOWN_REASON_CODES = listOf(
    "api_key_openai",
    "api_key_anthropic",
    "github_token",
    "aws_access_key",
    "aws_secret_key",
    "private_key_pem",
    "generic_bearer",
    "card",
    "email",
    "phone",
    "base64_secret",
    "split_secret",
    "generated_secret",
    "system_prompt_leak",
    "suspicious_url",
    "dangerous_command",
    "pii_echo",
    "secret_in_history",
)

class GatewayUiMapperTest {

    @Test
    fun toGatewayReasonLabel_onEveryKnownDetectorCode_neverFallsBackToUnknown() {
        KNOWN_REASON_CODES.forEach { code ->
            val label = code.toGatewayReasonLabel()

            assertNotEquals("неизвестная причина", label, "code=$code")
        }
    }

    @Test
    fun toGatewayReasonLabel_onSecretInHistory_explainsItIsFromEarlierMessage() {
        val label = "secret_in_history".toGatewayReasonLabel()

        assertEquals("секрет найден в более раннем сообщении этого чата, не в последнем", label)
    }

    @Test
    fun toGatewayReasonLabel_onTrulyUnknownCode_fallsBackToUnknown() {
        val label = "totally_unmapped_code".toGatewayReasonLabel()

        assertEquals("неизвестная причина", label)
    }
}
