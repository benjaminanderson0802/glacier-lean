from conftest import Server


def test_server_diagnostics_reads_backend_log_after_stop(tmp_path):
    server = Server(tmp_path)
    server.log.write("backend stderr diagnostic marker\n")
    server.stop()

    assert "backend stderr diagnostic marker" in server.diagnostics()
