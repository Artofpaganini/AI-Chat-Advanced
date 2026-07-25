package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboard
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import kotlinx.coroutines.launch

private const val BULLET_SYMBOL = "•"
private const val NUMBERED_ITEM_SUFFIX = "."
private const val CODE_BACKGROUND_ALPHA = 0.14f
private const val HEADING_LEVEL_ONE = 1
private const val HEADING_LEVEL_TWO = 2
private const val COPY_CODE_CONTENT_DESCRIPTION = "Copy code block"

@Composable
internal fun MarkdownText(
    text: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
) {
    val blocks = remember(text) { parseMarkdown(text) }
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(ChatDimens.spacingXs)) {
        blocks.forEach { block ->
            when (block) {
                is MarkdownBlock.Paragraph -> Text(text = block.spans.toAnnotatedString(), style = style)
                is MarkdownBlock.Heading -> Text(text = block.spans.toAnnotatedString(), style = headingStyle(level = block.level))
                is MarkdownBlock.BulletItem -> MarkdownListItem(marker = BULLET_SYMBOL, spans = block.spans, style = style)
                is MarkdownBlock.NumberedItem -> MarkdownListItem(
                    marker = "${block.number}$NUMBERED_ITEM_SUFFIX",
                    spans = block.spans,
                    style = style,
                )
                is MarkdownBlock.CodeBlock -> MarkdownCodeBlock(language = block.language, code = block.code, style = style)
            }
        }
    }
}

@Composable
private fun headingStyle(level: Int): TextStyle {
    val baseStyle = when (level) {
        HEADING_LEVEL_ONE -> MaterialTheme.typography.titleLarge
        HEADING_LEVEL_TWO -> MaterialTheme.typography.titleMedium
        else -> MaterialTheme.typography.titleSmall
    }
    return baseStyle.copy(fontWeight = FontWeight.Bold)
}

@Composable
private fun MarkdownListItem(
    marker: String,
    spans: List<MarkdownSpan>,
    style: TextStyle,
) {
    Row(horizontalArrangement = Arrangement.spacedBy(ChatDimens.spacingXs)) {
        Text(text = marker, style = style)
        Text(text = spans.toAnnotatedString(), style = style)
    }
}

@Composable
private fun MarkdownCodeBlock(
    language: String?,
    code: String,
    style: TextStyle,
) {
    val clipboard = LocalClipboard.current
    val coroutineScope = rememberCoroutineScope()
    val codeBackground = LocalContentColor.current.copy(alpha = CODE_BACKGROUND_ALPHA)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(color = codeBackground, shape = MaterialTheme.shapes.small)
            .padding(ChatDimens.spacingXs),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(text = language.orEmpty(), style = MaterialTheme.typography.labelSmall)
            IconButton(
                onClick = {
                    coroutineScope.launch {
                        clipboard.setClipEntry(createPlainTextClipEntry(code))
                    }
                },
            ) {
                Icon(imageVector = Icons.Filled.ContentCopy, contentDescription = COPY_CODE_CONTENT_DESCRIPTION)
            }
        }
        Text(
            text = code,
            style = style.copy(fontFamily = FontFamily.Monospace),
            modifier = Modifier.horizontalScroll(rememberScrollState()),
        )
    }
}

@Composable
private fun List<MarkdownSpan>.toAnnotatedString(): AnnotatedString {
    val codeBackground = LocalContentColor.current.copy(alpha = CODE_BACKGROUND_ALPHA)
    return remember(this, codeBackground) {
        buildAnnotatedString {
            forEach { span ->
                when {
                    span.isBold -> withStyle(SpanStyle(fontWeight = FontWeight.Bold)) { append(span.text) }
                    span.isItalic -> withStyle(SpanStyle(fontStyle = FontStyle.Italic)) { append(span.text) }
                    span.isCode -> withStyle(
                        SpanStyle(fontFamily = FontFamily.Monospace, background = codeBackground),
                    ) { append(span.text) }
                    else -> append(span.text)
                }
            }
        }
    }
}
