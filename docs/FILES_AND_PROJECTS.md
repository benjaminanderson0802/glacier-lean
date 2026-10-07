# Files and projects

Glacier keeps uploaded originals on the machine running the backend. The default upload limit is 50 MB per file; set `GLACIER_MAX_UPLOAD_MB` before starting Glacier to change it. Executable and script files are refused by extension, and common executable signatures are refused even when the file is renamed.

Uploads go to `GLACIER_HOME/files/<project>/<file name>`. An upload without a project goes into **Inbox**. If MarkItDown can read the file, Glacier also saves a Markdown note under `GLACIER_HOME/vault/files/<project>/` and indexes its text in memory search. The note links to the original file. Unreadable formats remain available as originals without a converted note.

## API

- `POST /api/files`: multipart form with `file` and optional `project` fields. Returns the file name, project, size, SHA-256 digest, stored path, converted note path (when available), and whether the upload was a duplicate.
- `GET /api/files?project=Research`: lists saved files, optionally within one project.
- `GET /api/projects`: lists projects and their file counts. Inbox is listed even before its first upload.
- `POST /api/projects`: JSON body such as `{"name":"Field Notes"}` creates a project folder.

Project and file names accept letters, numbers, spaces, hyphens, underscores, parentheses, and periods. Names must be a single safe Windows-compatible name. Executables, traversal paths, and oversized uploads receive plain error messages. Uploads are copied in 1 MB chunks to a temporary file while Glacier calculates a SHA-256 digest. Each project has an atomically updated `.index.json` for listings and duplicate checks. Uploads above the configured limit are rejected while streaming; the request is rejected early when its declared size exceeds the limit plus multipart overhead. Identical content in the same project returns the existing file entry rather than saving another copy; the same content may be stored separately in another project. Readable document conversion runs in a separate process with a 60 second time limit, a 2 MB text cap, and a 1 GB address-space cap where the operating system provides `resource.setrlimit`. Windows does not have this memory cap. If conversion or note indexing fails, the original remains saved and the response explains that its text could not be read.
