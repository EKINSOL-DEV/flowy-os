# Commit Command

Updates DEV_LOG.md with recent changes and commits all modifications to git.

## Usage

```
/commit [optional commit message]
```

## What it does

1. **Analyzes recent changes**: Reviews git status and diff to understand what was modified
2. **Updates DEV_LOG.md**: Adds a new entry with timestamp, author, and detailed change summary
3. **Commits changes**: Stages and commits all modifications with a descriptive message
4. **Provides summary**: Shows what was committed and the current git status

## Examples

```bash
# Basic commit with auto-generated message
/commit

# Commit with custom message
/commit "Fix authentication bug in user login"

# Commit with detailed description
/commit "Add new documentation portal with search functionality"
```

## Features

- **Auto-timestamps**: Uses current UTC time for DEV_LOG.md entries
- **Smart change detection**: Analyzes file modifications to create meaningful log entries
- **Consistent formatting**: Follows existing DEV_LOG.md structure and conventions
- **Git integration**: Handles staging, committing, and status reporting
- **Error handling**: Provides clear feedback if commit fails or no changes exist

## File Impact

- Updates `DEV_LOG.md` with new entry
- Commits all staged and unstaged changes
- Maintains git history with descriptive commit messages