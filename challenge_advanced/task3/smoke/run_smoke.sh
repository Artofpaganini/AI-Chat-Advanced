#!/usr/bin/env bash
# L2 smoke-раннер по adb для AI-Chat-Advanced. Прогоняет сценарии из scenarios.md,
# снимает скрин на каждом шаге, пишет report.md с PASS/FAIL + диагнозом.
# Использование: ./run_smoke.sh  (эмулятор/девайс должен быть подключён; APK собран)
set -u
export PATH="$PATH:$HOME/Library/Android/sdk/platform-tools"
PKG="com.jarvis.chat.dev.debug"
ACT="$PKG/com.jarvis.chat.android.MainActivity"
APK="$(git rev-parse --show-toplevel 2>/dev/null)/androidApp/build/outputs/apk/dev/debug/androidApp-dev-debug.apk"
OUT="$(dirname "$0")/shots"; mkdir -p "$OUT"
REPORT="$(dirname "$0")/report.md"

shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null; echo "  📸 $1.png"; }
dump(){ adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb shell cat /sdcard/ui.xml 2>/dev/null; }
alive(){ adb shell pidof "$PKG" >/dev/null 2>&1 && echo up || echo down; }
fatal(){ adb logcat -d -t 200 2>/dev/null | grep -c -E "FATAL EXCEPTION|AndroidRuntime" ; }
# tap по центру элемента, найденного по подстроке text/content-desc в ui-дампе
tap_text(){ local q="$1"; local b; b=$(dump | tr '>' '\n' | grep -iE "text=\"[^\"]*$q|content-desc=\"[^\"]*$q" | grep -oE 'bounds="\[[0-9,]+\]\[[0-9,]+\]"' | head -1); \
  [ -z "$b" ] && { echo "  ⚠ не нашёл '$q'"; return 1; }; \
  local c; c=$(echo "$b" | grep -oE '[0-9]+' ); local x1=$(echo "$c"|sed -n 1p) y1=$(echo "$c"|sed -n 2p) x2=$(echo "$c"|sed -n 3p) y2=$(echo "$c"|sed -n 4p); \
  adb shell input tap $(((x1+x2)/2)) $(((y1+y2)/2)); }

echo "# Smoke report - $(date '+%F %T')" > "$REPORT"
echo "Device: $(adb shell getprop ro.product.model 2>/dev/null) · APK: $APK" >> "$REPORT"
echo "" >> "$REPORT"; echo "| Сценарий | Результат | Скрины | Комментарий |" >> "$REPORT"; echo "|---|---|---|---|" >> "$REPORT"

echo "== install =="; adb install -r -d "$APK" 2>&1 | tail -1

# S1 cold start
echo "== S1 cold start =="; adb shell am start -n "$ACT" >/dev/null 2>&1; adb shell sleep 4; shot s1_launch
S1=$([ "$(alive)" = up ] && dump | grep -qiE 'Send|Jarvis|EditText|input' && echo PASS || echo FAIL)
echo "| S1 cold start | $S1 | s1_launch | alive=$(alive) |" >> "$REPORT"

# S2 send
echo "== S2 send =="; tap_text "" 2>/dev/null; adb shell input tap 360 1180; adb shell input text "Privet" ; shot s2_typed
tap_text "Send" || adb shell input keyevent 66; adb shell sleep 2; shot s2_sending; adb shell sleep 12; shot s2_reply
S2=$([ "$(fatal)" -eq 0 ] && echo PASS || echo FAIL)
echo "| S2 send | $S2 | s2_typed,s2_sending,s2_reply | fatal=$(fatal) |" >> "$REPORT"

# S3 favorite + filter
echo "== S3 favorite =="; tap_text "star\|избранн\|favorite" 2>/dev/null; shot s3_fav; tap_text "filter\|избранн" 2>/dev/null; shot s3_filter
echo "| S3 favorite/filter | manual-check | s3_fav,s3_filter | сверить фильтр по скринам |" >> "$REPORT"

# S4 export/import
echo "== S4 export/import =="; tap_text "export\|экспорт" 2>/dev/null; shot s4_export; tap_text "import\|импорт" 2>/dev/null; adb shell sleep 2; shot s4_import
echo "| S4 export/import | manual-check | s4_export,s4_import | сверить снэкбар/рост списка |" >> "$REPORT"

# S5 persistence
echo "== S5 persistence =="; N1=$(dump | grep -c -iE 'bubble\|message'); adb shell am force-stop "$PKG"; adb shell sleep 2; adb shell am start -n "$ACT" >/dev/null 2>&1; adb shell sleep 4; shot s5_relaunch; N2=$(dump | grep -c -iE 'bubble\|message')
S5=$([ "$N2" -ge 1 ] && echo PASS || echo "CHECK")
echo "| S5 persistence | $S5 | s5_relaunch | before~$N1 after~$N2 |" >> "$REPORT"

echo "" >> "$REPORT"; echo "Скрины: \`shots/\`. FATAL в logcat: $(fatal)." >> "$REPORT"
echo "=== готово: $REPORT ==="; cat "$REPORT"
