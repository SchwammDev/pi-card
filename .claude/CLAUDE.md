# Code Principles

Code should communicate intent. Write it so that any person or agent can understand it in 6 months without comments — comments rot, clear names and structure don't.

- Prefer simple, readable solutions over clever ones
- Small functions with single responsibility — each function is one named thought
- Respect the existing codebase. Change what needs changing, nothing more. Don't rewrite, reformat, or add things that weren't asked for.
- When unsure about a change, ask. Don't guess on decisions that affect working code.
- Write tests before the production code they cover, and observe them fail before implementing. A test that was never red doesn't prove the behavior is specified — it only echoes what the code already happens to do.
