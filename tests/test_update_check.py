from unittest.mock import MagicMock, patch

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


def _github_response(tag):
    return MagicMock(
        raise_for_status=lambda: None,
        json=lambda: {"tag_name": tag, "html_url": f"https://example/tag/{tag}"},
    )


def test_auto_apply_patch_triggers_wrapper_when_flag_on():
    from enferno.tasks import maintenance

    fake_redis = MagicMock()
    fake_redis.get.return_value = None  # nothing notified yet
    with (
        patch.object(maintenance, "cfg", MagicMock(AUTO_APPLY_PATCH_UPDATES=True)),
        patch.object(maintenance, "requests") as req,
        patch.object(maintenance, "rds", fake_redis),
        patch.object(maintenance, "subprocess") as sp,
        patch.object(maintenance, "_current_version", return_value="4.1.0"),
        patch.object(maintenance, "Notification") as notif,
    ):
        req.get.return_value = _github_response("v4.1.1")
        maintenance.check_for_updates.run()
        sp.run.assert_called_once()
        args = sp.run.call_args.args[0]
        assert args == ["sudo", "-n", "/usr/local/sbin/bayanat-start-update"]
        notif.create_for_admins.assert_not_called()


def test_auto_apply_off_falls_back_to_notification():
    from enferno.tasks import maintenance

    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with (
        patch.object(maintenance, "cfg", MagicMock(AUTO_APPLY_PATCH_UPDATES=False)),
        patch.object(maintenance, "requests") as req,
        patch.object(maintenance, "rds", fake_redis),
        patch.object(maintenance, "subprocess") as sp,
        patch.object(maintenance, "_current_version", return_value="4.1.0"),
        patch.object(maintenance, "Notification") as notif,
    ):
        req.get.return_value = _github_response("v4.1.1")
        maintenance.check_for_updates.run()
        sp.run.assert_not_called()
        notif.create_for_admins.assert_called_once()


def test_auto_apply_on_but_minor_bump_still_notifies():
    from enferno.tasks import maintenance

    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    with (
        patch.object(maintenance, "cfg", MagicMock(AUTO_APPLY_PATCH_UPDATES=True)),
        patch.object(maintenance, "requests") as req,
        patch.object(maintenance, "rds", fake_redis),
        patch.object(maintenance, "subprocess") as sp,
        patch.object(maintenance, "_current_version", return_value="4.1.0"),
        patch.object(maintenance, "Notification") as notif,
    ):
        req.get.return_value = _github_response("v4.2.0")
        maintenance.check_for_updates.run()
        sp.run.assert_not_called()
        notif.create_for_admins.assert_called_once()
