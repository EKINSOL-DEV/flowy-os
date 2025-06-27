#!/bin/bash

# /commit command - Update DEV_LOG.md and commit changes
# Usage: /commit [optional commit message]

set -e

COMMIT_MSG="$*"
TIMESTAMP=$(date -u +"%H:%M UTC")
DATE=$(date -u +"%Y-%m-%d")
AUTHOR="Nicky Goethals"

echo "🔄 Analyzing changes and updating DEV_LOG.md..."

# Check if there are any changes to commit
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "ℹ️  No changes to commit."
    exit 0
fi

# Get git status and diff for analysis
GIT_STATUS=$(git status --porcelain)
GIT_DIFF=$(git diff --name-only HEAD 2>/dev/null || git diff --name-only --cached)

# Analyze changes to create DEV_LOG entry
echo "📝 Creating DEV_LOG.md entry..."

# Determine what type of changes were made
CHANGES_SUMMARY=""
if echo "$GIT_STATUS" | grep -q "start-dev.sh"; then
    CHANGES_SUMMARY="Enhanced development environment automation"
elif echo "$GIT_STATUS" | grep -q "README.md"; then
    CHANGES_SUMMARY="Updated project documentation"
elif echo "$GIT_STATUS" | grep -q "docker/flink-jobmanager"; then
    CHANGES_SUMMARY="Improved Flink job deployment and configuration"
elif echo "$GIT_STATUS" | grep -q "dev-tools"; then
    CHANGES_SUMMARY="Enhanced development tools and monitoring"
elif echo "$GIT_STATUS" | grep -q ".py"; then
    CHANGES_SUMMARY="Updated Python code and functionality"
elif echo "$GIT_STATUS" | grep -q ".sh"; then
    CHANGES_SUMMARY="Improved shell scripts and automation"
else
    CHANGES_SUMMARY="General project improvements and updates"
fi

# Use custom commit message if provided, otherwise generate one
if [ -n "$COMMIT_MSG" ]; then
    FINAL_COMMIT_MSG="$COMMIT_MSG"
    LOG_TITLE="$COMMIT_MSG"
else
    FINAL_COMMIT_MSG="$CHANGES_SUMMARY"
    LOG_TITLE="$CHANGES_SUMMARY"
fi

# Create temporary file with new DEV_LOG entry
TEMP_LOG=$(mktemp)

# Read current DEV_LOG.md and find where to insert new entry
if [ -f "DEV_LOG.md" ]; then
    # Extract header and find insertion point
    awk '
    BEGIN { found_date = 0; printed_entry = 0 }
    /^## [0-9]{4}-[0-9]{2}-[0-9]{2}$/ {
        if (!printed_entry && $2 == "'"$DATE"'") {
            # Same date exists, add to it
            print $0
            print ""
            print "### ✅ '"$LOG_TITLE"'"
            print "**Time:** '"$TIMESTAMP"'"
            print "**Author:** '"$AUTHOR"'"
            print ""
            print "**Changes:**"
            print "- '"$(echo "$GIT_STATUS" | head -5 | sed 's/^../- /' | tr '\n' ' ' | sed 's/- $//')..."'"
            print ""
            print "**Files Modified:**"
            while ((getline line < "/dev/stdin") > 0) {
                if (line ~ /^[AM?]/) {
                    gsub(/^[AM?][[:space:]]*/, "", line)
                    print "- " line
                }
            }
            print ""
            print "**Benefits:**"
            print "- Improved development workflow and reliability"
            print "- Enhanced system functionality and user experience"
            print ""
            print "---"
            print ""
            printed_entry = 1
            next
        } else if (!printed_entry) {
            # Different date, insert new date section
            print "## '"$DATE"'"
            print ""
            print "### ✅ '"$LOG_TITLE"'"
            print "**Time:** '"$TIMESTAMP"'"
            print "**Author:** '"$AUTHOR"'"
            print ""
            print "**Changes:**"
            print "- '"$(echo "$GIT_STATUS" | head -3 | sed 's/^..//' | tr '\n' ' ')..."'"
            print ""
            print "**Benefits:**"
            print "- Improved development workflow and reliability"
            print "- Enhanced system functionality and user experience"
            print ""
            print "---"
            print ""
            printed_entry = 1
        }
    }
    { print }
    END {
        if (!printed_entry) {
            # No date sections found, add at beginning after header
            print ""
            print "## '"$DATE"'"
            print ""
            print "### ✅ '"$LOG_TITLE"'"
            print "**Time:** '"$TIMESTAMP"'"
            print "**Author:** '"$AUTHOR"'"
            print ""
            print "**Changes:**"
            print "- '"$(echo "$GIT_STATUS" | head -3 | sed 's/^..//' | tr '\n' ' ')..."'"
            print ""
            print "**Benefits:**"
            print "- Improved development workflow and reliability"
            print "- Enhanced system functionality and user experience"
            print ""
            print "---"
        }
    }' DEV_LOG.md > "$TEMP_LOG"
    
    # Replace original with updated version
    mv "$TEMP_LOG" DEV_LOG.md
else
    echo "⚠️  DEV_LOG.md not found, skipping log update"
fi

echo "📦 Staging changes..."
git add .

echo "✅ Committing changes..."
git commit -m "$FINAL_COMMIT_MSG"

echo "📊 Git status after commit:"
git status --short

echo ""
echo "🎉 Successfully committed changes!"
echo "📝 DEV_LOG.md updated with entry: $LOG_TITLE"
echo "💾 Commit message: $FINAL_COMMIT_MSG"