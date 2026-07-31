package com.jarvis.chat.core.micromodel.inference

private const val YO_LOWER = 'ё'
private const val E_LOWER = 'е'
private const val DIGIT_PLACEHOLDER = '0'
private const val SPACE_CHAR = ' '

internal object MicroModelTextNormalizer {

    fun normalize(text: String): String {
        val lowercased = text.lowercase()
        val builder = StringBuilder(lowercased.length)
        for (character in lowercased) {
            builder.append(character.toNormalizedChar())
        }
        return collapseSpaces(builder.toString()).trim(SPACE_CHAR)
    }

    private fun Char.toNormalizedChar(): Char = when {
        this == YO_LOWER -> E_LOWER
        isDigit() -> DIGIT_PLACEHOLDER
        isLetter() || this == SPACE_CHAR -> this
        else -> SPACE_CHAR
    }

    private fun collapseSpaces(text: String): String {
        val builder = StringBuilder(text.length)
        var previousWasSpace = false
        for (character in text) {
            if (character == SPACE_CHAR) {
                if (!previousWasSpace) {
                    builder.append(character)
                }
                previousWasSpace = true
            } else {
                builder.append(character)
                previousWasSpace = false
            }
        }
        return builder.toString()
    }
}
