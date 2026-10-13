# Visual refresh checkpoint

The complete pre-refresh source snapshot is stored locally at:

- Ref: `checkpoint/pre-playful-20261001`
- Commit: `aa580859d7d30b1a51d12b076d34715a99b1ff77`
- Includes all 126 non-ignored project files, including files that were untracked.

The playful refresh changes `web/live.html` and `web/styles.css`. The Python
engine and browser routing logic retain their checkpoint contents.

To revert only this visual refresh after choosing to roll back, run from the
repository root:

```sh
git restore --source=checkpoint/pre-playful-20261001 --worktree -- web/live.html web/styles.css
```

Then reload the browser. This command replaces the two visual files; save any
later edits to them first. It leaves the other project files and the Git index
alone. The checkpoint is local and has not been pushed.
