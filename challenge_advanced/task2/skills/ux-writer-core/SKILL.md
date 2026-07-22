---
name: ux-writer-core
description: "Shared UX-writer rules for xbet-writer-expert and alva-writer-expert: writing style (STRICT), UX copywriting checklist, resource-string conventions, localization, documentation formats, output format. Domain specifics (resource system path, tone of voice, domain rules) live in the calling agent's body."
---

# UX Writer Core

Shared rules for any UX-writer agent. Domain-specific parts (resource system path, tone of voice, domain rules, communication roles) live in the calling agent's body.

## Стиль письма (STRICT)

Правила для любого текста, который пишет агент (документация, release notes, PR, примеры, ответы):

- **Простой язык.** Понятно джуну, мидлу и синьору. Без редких/узкоспециальных слов ("идиоматично", "детерминированно", "элиминировать" и т.п.) - бери простой эквивалент.
- **Короткий дефис.** Всегда "-", никогда длинное тире "—".
- **Никаких "- это".** Не пиши конструкцию "X - это Y". Выкидывай слово "это", оставляй простой дефис: "X - Y".
- **Никаких стрелок "→".** Вместо юникод-стрелки пиши ASCII "->" (дефис + больше). Касается схем, потоков, подписей ("экран -> хост").
- **Короткие примеры.** В примерах оставляй только суть, остальное сворачивай в `//...`:
  ```
  fun placeBet(id: String) {
      validate(id)
      //...
  }
  ```

## UX Copywriting

- Buttons, headers, labels, placeholders, hints
- Error messages: clear, actionable (tone per calling agent)
- Empty states: helpful, guiding users to next action
- Onboarding flows: concise, progressive disclosure
- Tooltips, snackbars, dialogs: short, direct
- Loading states, confirmation messages

## Resource Strings

Concrete resource system (Android `strings.xml` / KMP `composeResources/` path) - see calling agent.

- Naming convention: `<screen>_<element>_<description>` (e.g. `login_button_submit`, `profile_error_network`)
- Use plurals for countable items
- Use string formatting (`%s`, `%d`) for dynamic content
- Detect and prevent duplicate string keys across modules
- Keep strings translatable - no concatenation of translated fragments
- All strings externalized - no hardcoded text in code

## Localization

- Prepare texts for multi-language support
- Handle plural forms for different locales
- Consider text expansion (German ~30% longer than English)
- Right-to-left (RTL) text considerations

## Documentation

- Release notes: user-facing, clear, grouped by feature/fix
- Changelog: developer-facing, with ticket references
- README updates when relevant
- PR descriptions: summary, what changed, how to test

## Output Format

For UX copy tasks:
```
## Screen: [screen name]

| Key | Text | Notes |
|-----|------|-------|
| screen_element_desc | "Text here" | Context/rationale |
```

For resource strings:
```xml
<string name="screen_element_desc">Text here</string>
```

## Generic Rules

- Keep button text to 1-3 words when possible
- Error messages must always tell the user what to do next
- No jargon without explanation for user-facing text
- Same term for same concept across the entire app
