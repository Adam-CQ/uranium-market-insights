# Publish source from a separate clean repository

Publishing is a manual owner action after reviewing the local changes. This
checkout's existing Git state and remotes must remain untouched.

1. Review product behavior, tests, data rights, deployment prerequisites and the
   code licence decision. Choose a licence before publishing application code.
2. Export reviewed source files to a new destination directory without `.git`,
   `.env*`, credentials, raw/processed data, virtual environments, node_modules,
   caches, test outputs or backups. Retain product tests and permitted fixtures.
3. Inspect the exported files for secrets and restricted content. Run the checks
   in [verification-commands.md](verification-commands.md) from the new directory.
4. Initialise a fresh Git repository there, create an initial commit, inspect its
   complete file list, and attach a new empty production remote. Push only when
   ready to publish.

Do not merge previous Git history, rewrite existing branches, or change this
checkout's remotes. Source data reuse policies do not license the app code.
