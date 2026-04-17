from enferno.tasks.maintenance import _strip_v, _is_patch_bump


def test_strip_v_prefix():
    assert _strip_v("v4.1.0") == "4.1.0"
    assert _strip_v("4.1.0") == "4.1.0"
    assert _strip_v("") == ""


def test_is_patch_bump_true():
    assert _is_patch_bump("4.1.0", "4.1.1") is True
    assert _is_patch_bump("4.1.2", "4.1.10") is True


def test_is_patch_bump_false_for_minor():
    assert _is_patch_bump("4.1.0", "4.2.0") is False


def test_is_patch_bump_false_for_major():
    assert _is_patch_bump("4.1.0", "5.0.0") is False


def test_is_patch_bump_false_for_same():
    assert _is_patch_bump("4.1.0", "4.1.0") is False


def test_is_patch_bump_false_for_downgrade():
    assert _is_patch_bump("4.1.5", "4.1.3") is False
