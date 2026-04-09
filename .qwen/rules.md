# Project Rules & Conventions

## 🛑 Mandatory Workflow Rules

### Before Every Commit
1. ALWAYS ask user before committing — never run `git commit` without explicit approval
2. Show commit message to user for review/editing before committing
3. Ask about version bump (PATCH/MINOR/MAJOR) after changes to code
4. Ask about push to GitHub after commit

---

## 📦 Commit Strategy

### When to Commit
Commit ONLY when one of these occurs:
1. **New feature implemented** — marked with `TODO:` in code
2. **Bug fix** — marked with `FIXME:` in code  
3. **Significant change** — major refactor, breaking change, or important improvement

### When NOT to Commit
- Minor typos fixes
- Small code style changes
- Single line fixes
- Documentation tweaks
- Fix text syntax or small style error in code or documentation
- Changes to `.qwen/*` files (rules, context, metadata) — do NOT mention in commit messages

---

## 📋 Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
type: short description

- Bullet point for each change
- Keep it concise
```

**Types:**
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `style:` — code style (formatting, no logic changes)
- `refactor:` — code refactor (no behavior changes)
- `test:` — adding/updating tests
- `chore:` — maintenance tasks

---

## 🏷️ Code Markers

| Marker | Meaning | Commit? |
|--------|---------|---------|
| `TODO:` | New feature to implement | ✅ Yes, when done |
| `FIXME:` | Bug/crack to fix | ✅ Yes, when fixed |

---

## 📁 Project Structure Notes

- Core script: `lfm/lfm.py`
- Config: `lfm/lfm.ini`
- Context: `.qwen/QWEN.md`
- Rules: `.qwen/rules.md`
- Binaries: `lfm/ffmpeg/` (large files, tracked in git)

---

*Last updated: 2026-04-09*
*Version at time: 0.8.2*
