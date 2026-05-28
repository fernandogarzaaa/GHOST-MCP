---
description: Ingest a file/directory/email into Ghost's personal memory.
---

$ARGUMENTS is the path. Infer `kind` from the path (directory → directory, .mbox/.eml → email_file, else file). Call `ghost_ingest` and report the resulting chunk count.
