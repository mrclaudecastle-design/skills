---
name: safe-mac-work
description: Work on the owner's Mac without losing or changing anything. Add only, plain mounts, report refusals.
---

# Safe Mac work

## If you're picking this up
- **What it is:** the rules for working on this Mac and its drive.
- **Where the files are:** work goes in the build folder you were given (new files only). Read-only: the shared models folder, the notes vaults, other threads' folders.
- **How to check it worked:** after writing, list the file and read it back. After a drop, re-check every file you care about.
- **What's next:** report what you changed and anything refused.
- **Rules:** never delete, move, rename or overwrite anything. New names only. One model job at a time. No downloads, installs, sign-ups, purchases or git pushes without the owner's own yes.

## Steps
1. Read the folder before writing. If a name exists, pick another.
2. Never edit a script while it is running, or one that a queue is about to use. Copy it to a new name.
3. Read a whole command before running it. Remove any delete or tidy-up step.
4. Search only named folders. Never from the top of the disk or across `/Volumes`.
5. Never write to the backup drive, `~/Downloads`, or any volume the owner has not opened to you.
6. **If the work drive drops:** `diskutil apfs list`, find it by NAME. Unlocked: a plain `diskutil mount`. Locked: never handle a password; report and wait. Re-check files after it returns. Three drops in an hour: stop and report. Restart any job that lost its folder.
7. **If a step is refused** by the permission check: stop, say what was refused, and wait. Don't reach the same result another way. Don't change permission settings.
8. A log line that says "valid" or "done" isn't proof. Check it.
9. If you reported something wrong, say so as a correction, with the old value and the new one.

## Report form
Result, what changed, faults, what was not done, what was refused, what only the owner can do.
