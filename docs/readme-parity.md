# README parity checklist

This checklist helps maintain parity between the English README (`README.md`) and the Simplified Chinese README (`README.zh-CN.md`). For every documentation change, please ensure that both files remain structurally consistent. The content does not have to be a word‑for‑word translation, but the sections, examples, and images should appear in both files in the same order.

| Section | README.md | README.zh-CN.md | Notes |
| --- | --- | --- | --- |
| Title and tagline | ✓ | ✓ | Titles and taglines should clearly explain what ccproxy does. |
| Language links | ✓ | ✓ | Both files link to each other at the top. |
| Hero image | ✓ | ✓ | Use the same `docs/assets/readme-hero-new.png` with different alt text. |
| Introduction | ✓ | ✓ | Explain why ccproxy exists and how it bridges Anthropic and OpenAI interfaces. |
| Why/Features | ✓ | ✓ | Describe the benefits of using ccproxy. |
| Quick start | ✓ | ✓ | Show installation commands for both Unix and Windows. |
| Provider selection table | ✓ | ✓ | Same rows and notes for each provider. |
| Usage examples | ✓ | ✓ | Provide similar commands demonstrating `ccproxy model` and `ccproxy run`. |
| ChatGPT subscription note | ✓ | ✓ | Explain that the subscription token stays local and is not converted to an OpenAI API key. |
| Local security boundary | ✓ | ✓ | Include the same diagram `local-security-diagram-new.png` and explain where keys reside. |
| Troubleshooting | ✓ | ✓ | List the same symptoms, causes, and fixes. |
| Advanced links | ✓ | ✓ | Link to architecture, providers, testing, contributing, roadmap. |
| Contributing section | ✓ | ✓ | Encourage contributions and mention the parity requirement. |

When updating either README:

1. Copy the relevant section into the other language’s file and translate it appropriately.
2. Ensure code blocks and command outputs remain the same.
3. Run the CI script (`scripts/check_readme_parity.py`) if available, to verify both files match the defined structure.

Maintaining parity makes it easier for users and contributors to access up‑to‑date documentation in their preferred language.