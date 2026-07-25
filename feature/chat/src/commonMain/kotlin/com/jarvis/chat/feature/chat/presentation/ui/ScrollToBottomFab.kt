package com.jarvis.chat.feature.chat.presentation.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier

private const val SCROLL_TO_BOTTOM_CONTENT_DESCRIPTION = "Scroll to bottom"

@Composable
internal fun ScrollToBottomFab(
    listState: LazyListState,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isVisible by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            val lastVisibleIndex = layoutInfo.visibleItemsInfo.lastOrNull()?.index
            val lastItemIndex = layoutInfo.totalItemsCount - 1
            lastVisibleIndex != null && lastVisibleIndex < lastItemIndex
        }
    }

    AnimatedVisibility(
        visible = isVisible,
        enter = fadeIn() + scaleIn(),
        exit = fadeOut() + scaleOut(),
        modifier = modifier,
    ) {
        FloatingActionButton(onClick = onClick) {
            Icon(
                imageVector = Icons.Filled.KeyboardArrowDown,
                contentDescription = SCROLL_TO_BOTTOM_CONTENT_DESCRIPTION,
            )
        }
    }
}
