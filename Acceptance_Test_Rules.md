# Acceptance Test Rules

1. **Name tests as behaviors** — test names should clearly describe what the system does. The name alone should be a readable spec.

2. **Use domain language** — tests read like specs. Use terms from the project domain (wake word, utterance, response, follow-up, silence timeout), not implementation terms (buffer, queue, callback).

3. **One behavior per test** — each test asserts one expected behavior.

4. **Assertions are DSL too** — use well-named domain-language assert functions (e.g., `assert_assistant_spoke_response()`, `assert_led_is_pulsing_blue()`). Multiple assertions are fine within a test if they describe facets of the same behavior.

5. **Fake hardware, not logic** — pytest fixtures provide fake mic, speaker, LEDs, and API. Business logic runs real.

6. **DSL module** — reusable helper and assert functions live in a shared `dsl` module, not scattered across test files. These functions (e.g., `trigger_wake_word()`, `simulate_speech()`, `wait_for_silence()`) are the project's test DSL.

7. **Organize by feature** — acceptance tests live in a `features/` folder, one file per feature area:
   - `test_conversation_flow.py`
   - `test_wake_word.py`
   - `test_speech_to_text.py`
   - `test_ai_agent.py`
   - `test_text_to_speech.py`
   - `test_error_handling.py`
   - `test_configuration.py`

8. **No implementation coupling** — tests depend on public interfaces and observable behavior (spoke a response, LED changed, returned to wake-word mode), never on internal state or private methods.

9. **Tests are documentation** — if a behavior isn't covered by a test, it's not specified. The test suite is the living spec.
