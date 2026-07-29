package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.outlined.StarBorder
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboard
import androidx.compose.ui.text.font.FontWeight
import com.jarvis.chat.feature.chat.presentation.model.ChatMessageUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageRouteUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageStatusUiModel
import com.jarvis.chat.feature.chat.presentation.model.TriageUiModel
import kotlinx.coroutines.launch

private const val SPEAK_CONTENT_DESCRIPTION = "Speak message aloud"
private const val STOP_SPEAKING_CONTENT_DESCRIPTION = "Stop speaking"
private const val COPY_CONTENT_DESCRIPTION = "Copy message text"
private const val FAVORITE_ACTIVE_TEXT = "Remove from favorites"
private const val FAVORITE_INACTIVE_TEXT = "Add to favorites"
private const val COPY_MENU_ITEM_TEXT = "Copy"
private const val DELETE_MENU_ITEM_TEXT = "Delete"
private const val TRIAGE_LABEL_SEPARATOR = " · "
private const val TRIAGE_CONFIDENCE_PREFIX = "Уверенность: "
private const val TRIAGE_CONFIDENCE_SUFFIX = "%"
private const val TRIAGE_UNSURE_WARNING = "Не стоит полностью доверять этому ответу"
private const val TRIAGE_FAIL_WARNING = "Ассистент отказался отвечать"
private const val TRIAGE_CRISIS_WARNING = "Кризисная ситуация, нужно немедленное внимание"

@Composable
internal fun MessageBubble(
    message: ChatMessageUiModel,
    isTtsAvailable: Boolean,
    onSpeakToggle: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
    onCopy: () -> Unit,
    onDeleteRequest: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val isFromUser = message.isFromUser
    val bubbleColor = if (isFromUser) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val contentColor = if (isFromUser) {
        MaterialTheme.colorScheme.onPrimary
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    val clipboard = LocalClipboard.current
    val coroutineScope = rememberCoroutineScope()
    val copyMessage: () -> Unit = {
        coroutineScope.launch {
            clipboard.setClipEntry(createPlainTextClipEntry(message.text))
            onCopy()
        }
    }
    var isMenuExpanded by remember { mutableStateOf(false) }
    val menuInteractionSource = remember { MutableInteractionSource() }

    Box(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = if (isFromUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Surface(
            color = bubbleColor,
            contentColor = contentColor,
            shape = MaterialTheme.shapes.large,
            tonalElevation = ChatDimens.elevationLow,
            modifier = Modifier
                .widthIn(max = ChatDimens.messageBubbleMaxWidth)
                .combinedClickable(
                    interactionSource = menuInteractionSource,
                    indication = null,
                    onClick = {},
                    onLongClick = { isMenuExpanded = true },
                ),
        ) {
            Column(
                modifier = Modifier.padding(ChatDimens.spacingSm),
                horizontalAlignment = Alignment.Start,
            ) {
                MarkdownText(
                    text = message.text,
                    style = MaterialTheme.typography.bodyLarge,
                )
                Text(
                    text = message.timeLabel,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                message.modelId?.let { modelId ->
                    Text(
                        text = modelId,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                message.triage?.let { triage ->
                    TriageInfo(triage = triage)
                }
                MessageActions(
                    message = message,
                    isTtsAvailable = isTtsAvailable,
                    onSpeakToggle = onSpeakToggle,
                    onToggleFavorite = onToggleFavorite,
                    onCopy = copyMessage,
                )
            }
        }
        MessageContextMenu(
            expanded = isMenuExpanded,
            isFavorite = message.isFavorite,
            canFavorite = message.canFavorite,
            onDismiss = { isMenuExpanded = false },
            onCopy = copyMessage,
            onToggleFavorite = { onToggleFavorite(message.id) },
            onDelete = { onDeleteRequest(message.id) },
        )
    }
}

@Composable
private fun MessageContextMenu(
    expanded: Boolean,
    isFavorite: Boolean,
    canFavorite: Boolean,
    onDismiss: () -> Unit,
    onCopy: () -> Unit,
    onToggleFavorite: () -> Unit,
    onDelete: () -> Unit,
) {
    DropdownMenu(expanded = expanded, onDismissRequest = onDismiss) {
        DropdownMenuItem(
            text = { Text(text = COPY_MENU_ITEM_TEXT) },
            leadingIcon = { Icon(imageVector = Icons.Filled.ContentCopy, contentDescription = null) },
            onClick = {
                onCopy()
                onDismiss()
            },
        )
        if (canFavorite) {
            DropdownMenuItem(
                text = { Text(text = if (isFavorite) FAVORITE_ACTIVE_TEXT else FAVORITE_INACTIVE_TEXT) },
                leadingIcon = {
                    Icon(
                        imageVector = if (isFavorite) Icons.Filled.Star else Icons.Outlined.StarBorder,
                        contentDescription = null,
                    )
                },
                onClick = {
                    onToggleFavorite()
                    onDismiss()
                },
            )
        }
        DropdownMenuItem(
            text = { Text(text = DELETE_MENU_ITEM_TEXT) },
            leadingIcon = { Icon(imageVector = Icons.Filled.Delete, contentDescription = null) },
            onClick = {
                onDelete()
                onDismiss()
            },
        )
    }
}

@Composable
private fun MessageActions(
    message: ChatMessageUiModel,
    isTtsAvailable: Boolean,
    onSpeakToggle: (String) -> Unit,
    onToggleFavorite: (String) -> Unit,
    onCopy: () -> Unit,
) {
    Row(horizontalArrangement = Arrangement.Start) {
        if (message.isSpeakable && isTtsAvailable) {
            IconButton(onClick = { onSpeakToggle(message.id) }) {
                Icon(
                    imageVector = if (message.isSpeaking) Icons.Filled.Stop else Icons.AutoMirrored.Filled.VolumeUp,
                    contentDescription = if (message.isSpeaking) {
                        STOP_SPEAKING_CONTENT_DESCRIPTION
                    } else {
                        SPEAK_CONTENT_DESCRIPTION
                    },
                )
            }
        }
        IconButton(onClick = onCopy) {
            Icon(
                imageVector = Icons.Filled.ContentCopy,
                contentDescription = COPY_CONTENT_DESCRIPTION,
            )
        }
        if (message.canFavorite) {
            IconButton(onClick = { onToggleFavorite(message.id) }) {
                Icon(
                    imageVector = if (message.isFavorite) Icons.Filled.Star else Icons.Outlined.StarBorder,
                    contentDescription = if (message.isFavorite) FAVORITE_ACTIVE_TEXT else FAVORITE_INACTIVE_TEXT,
                )
            }
        }
    }
}

@Composable
private fun TriageInfo(triage: TriageUiModel, modifier: Modifier = Modifier) {
    if (triage.crisis) {
        Surface(
            modifier = modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
            shape = MaterialTheme.shapes.small,
        ) {
            Column(modifier = Modifier.padding(ChatDimens.spacingXs)) {
                Text(
                    text = TRIAGE_CRISIS_WARNING,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    fontWeight = FontWeight.Bold,
                )
                TriageInfoBody(
                    triage = triage,
                    routeColor = MaterialTheme.colorScheme.onErrorContainer,
                    mutedColor = MaterialTheme.colorScheme.onErrorContainer,
                )
            }
        }
    } else {
        Column(modifier = modifier) {
            TriageInfoBody(
                triage = triage,
                routeColor = triage.route.toRouteColor(),
                mutedColor = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun TriageInfoBody(triage: TriageUiModel, routeColor: Color, mutedColor: Color) {
    Text(
        text = "${triage.routeLabel}$TRIAGE_LABEL_SEPARATOR${triage.statusLabel}",
        style = MaterialTheme.typography.labelSmall,
        color = routeColor,
    )
    Text(
        text = "$TRIAGE_CONFIDENCE_PREFIX${triage.confidencePercent}$TRIAGE_CONFIDENCE_SUFFIX",
        style = MaterialTheme.typography.labelSmall,
        color = mutedColor,
    )
    when (triage.status) {
        TriageStatusUiModel.UNSURE -> Text(
            text = TRIAGE_UNSURE_WARNING,
            style = MaterialTheme.typography.labelSmall,
            color = if (triage.crisis) mutedColor else MaterialTheme.colorScheme.error,
            fontWeight = FontWeight.Bold,
        )
        TriageStatusUiModel.FAIL -> Text(
            text = TRIAGE_FAIL_WARNING,
            style = MaterialTheme.typography.labelSmall,
            color = if (triage.crisis) mutedColor else MaterialTheme.colorScheme.error,
            fontWeight = FontWeight.Bold,
        )
        TriageStatusUiModel.OK, TriageStatusUiModel.UNKNOWN -> Unit
    }
    Text(
        text = triage.explain,
        style = MaterialTheme.typography.labelSmall,
        color = mutedColor,
    )
}

@Composable
private fun TriageRouteUiModel.toRouteColor(): Color =
    when (this) {
        TriageRouteUiModel.EMERGENCY -> MaterialTheme.colorScheme.error
        TriageRouteUiModel.DOCTOR_SOON -> MaterialTheme.colorScheme.tertiary
        TriageRouteUiModel.PARENT_SUPPORT -> MaterialTheme.colorScheme.secondary
        TriageRouteUiModel.SELF_CARE,
        TriageRouteUiModel.OFF_TOPIC,
        TriageRouteUiModel.DATA_INSIGHT,
        TriageRouteUiModel.UNKNOWN,
        -> MaterialTheme.colorScheme.onSurfaceVariant
    }
