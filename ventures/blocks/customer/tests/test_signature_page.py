import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from ventures.blocks import customer


def test_signature_page_post_writes_pdf_and_audit(tmp_path):
    data_dir = tmp_path / "customer-data"
    document = tmp_path / "authorization.txt"
    document.write_text("Authorization terms", encoding="utf-8")
    request = customer.request_signature(document, {"name": "Jordan Signer", "email": "jordan@example.test"},
                                         data_dir=data_dir)
    server = customer.create_signature_server(data_dir, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(base + "/signature/" + request["id"]) as page_response:
            page = page_response.read().decode()
        assert "Review and sign" in page
        assert f"action=\"{base}/sign/{request['id']}\"" in page
        post = Request(base + "/sign/" + request["id"], data=urlencode({
            "typed_name": "Jordan Signer", "consent": "yes",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(post) as response:
            assert response.status == 200
            assert "Document signed" in response.read().decode()
        files = list((data_dir / "signed").glob("*-signed.pdf"))
        audits = list((data_dir / "signed").glob("*-audit.json"))
        assert len(files) == len(audits) == 1
        assert files[0].read_bytes().startswith(b"%PDF-")
        audit = json.loads(audits[0].read_text(encoding="utf-8"))
        assert audit["signer"] == "Jordan Signer"
        assert audit["document_sha256"] == request["document_sha256"]
        assert audit["signed_pdf_sha256"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
