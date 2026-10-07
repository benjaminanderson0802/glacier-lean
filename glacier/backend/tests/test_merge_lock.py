import workspaces


def test_merge_lock_closes_file_after_unlock(tmp_path):
    lock_file = open(tmp_path / "merge.lock", "a+")
    with workspaces._MergeLock(lock_file):
        assert not lock_file.closed
    assert lock_file.closed
