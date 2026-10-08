# Call a web API

Use **Call a web API** to send one HTTP request to a site you list in **Allowed sites**. It supports GET, POST, PUT, PATCH, and DELETE. POST, PUT, PATCH, and DELETE are marked as changing methods in the step catalogue so the Simple layout can warn about them.

Enter headers one per line as `Name: value`. The body can be text or JSON. In body and header values, `{prev_output}`, `{run}`, and `{env}` insert the previous step's output, this run's identifier, and this Environment's identifier. `{secret:NAME}` reads a saved secret from the operating system keychain. Secret placeholders are not allowed in the web address. Resolved secret values are removed from the step output and errors.

The request timeout defaults to 20 seconds. **Expected status** defaults to `2xx`; enter an exact status such as `201` to require that status. A response body is read up to 1 MB and output is limited to 20,000 characters. JSON responses are pretty-printed when the body format is set to JSON.

Glacier connects directly, checks the destination address, pins the connection to the checked address, and checks redirects. Private or local addresses are refused by default. Turn on **This API runs on this computer or my network** only when you trust the API on your computer or network.
