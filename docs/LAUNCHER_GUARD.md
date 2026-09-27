# Launcher-only engine startup

The player copy of `game/engine.exe` has a small entry-point gate. Without a live, one-use launcher capability, it displays “Please start the game using CoC Restored+.exe.” and exits before the original interface opens.

The launcher creates a randomly named Windows auto-reset event and supplies its name only to the child engine process. The gate opens and consumes the event, then continues at the original entry point. A second attempt with the same capability cannot consume it again. Handles are released when the game closes or startup fails.

This prevents accidental direct launches; it is not tamper-proof. It is an explicitly requested change, not original game behavior.

`tools/guard_engine.py` validates the original executable SHA-256 before adding one section and updating the PE headers. Existing code, resources and section addresses remain intact. The source archive's `game/creation.exe` is untouched. The client separately checks the exact hash of the guarded player executable.

Checks completed: one-use capability test; original section-byte preservation and patch hash test; direct-launch message observed; authorized native match startup. The packaged launcher also completed a match startup check without server errors.
