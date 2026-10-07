# Files and projects

Glacier keeps uploaded originals on the machine running the backend. The default upload limit is 50 MB per file; set `GLACIER_MAX_UPLOAD_MB` before starting Glacier to change it. Executable and script files (`.exe`, `.bat`, `.cmd`, `.ps1`, `.sh`, `.msi`) are refused.

Uploads go to `GLACIER_HOME/files/<project>/<file name>`. An upload without a project goes into **Inbox**. If MarkItDown can read the file, Glacier also saves a Markdown note under `GLACIER_HOME/vault/files/<project>/` and indexes its text in memory search. The note links to the original file. Unreadable formats remain available as originals without a converted note.

## API

- `POST /api/files`: multipart form with `file` and optional `project` fields. Returns the file name, project, size, SHA-256 digest, stored path, converted note path (when available), and whether the upload was a duplicate.
- `GET /api/files?project=Research`: lists saved files, optionally within one project.
- `GET /api/projects`: lists projects and their file counts. Inbox is listed even before its first upload.
- `POST /api/projects`: JSON body such as `{"name":"Field Notes"}` creates a project folder.

Project and file names accept letters, numbers, spaces, hyphens, underscores, parentheses, and periods. Names must be a single safe Windows-compatible name. Executables, traversal paths, and oversized uploads receive plain error messages. Uploading identical content to the same project returns the existing file entry rather than saving another copy; the same content may be stored separately in another project.
