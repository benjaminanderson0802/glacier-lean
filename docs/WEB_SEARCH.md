# Search the web

The **Search the web** step asks a SearXNG server you choose for search results. SearXNG is free and open source software. Glacier sends the search words to that server and returns a small list of titles, links, and snippets. It does not open the result links; use **Read a web page** as a separate step when you want to read a result.

## Run SearXNG on your computer

SearXNG's official installation guide covers Docker/Podman containers and package-based installs: <https://docs.searxng.org/admin/installation.html>. The container method usually does not require installing system packages, but it does require a container runtime such as Podman or Docker to already be available to your account.

For a local container, follow the official container instructions and publish its web port only on the local computer. For example, after creating a SearXNG settings file as described in the guide, run the official image with a local-only port mapping such as `127.0.0.1:8888:8080`. Then set **Search server** to `http://localhost:8888` in the step and turn on **The search server runs on this computer or my network**. The step refuses local and private network addresses unless you turn that option on.

If you cannot use a container runtime, the official guide also describes package and source installations. These may need administrator help or extra setup depending on your computer. SearXNG's JSON output must be enabled in its settings for Glacier to read search results; consult the official settings documentation if the server reports that JSON results are unavailable.

## Public search servers and privacy

A public SearXNG server can be easier to use, but its operator receives every search you send, including potentially sensitive words. The operator may keep logs or apply its own rules. Choose a server you trust, or run SearXNG yourself. A public server also sends your request onward to the search services configured by that server's operator.

The server address is shown in this step's settings. Glacier sends only the search request to that address; it does not send cookies, credentials, or API keys, and it does not fetch result links. Do not put private information or secret placeholders in the search words or server address.
