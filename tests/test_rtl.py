def test_arabic_layout_enables_rtl(app, anonymous_client, monkeypatch):
    monkeypatch.setitem(app.config, "BABEL_DEFAULT_LOCALE", "ar")

    response = anonymous_client.get("/login")

    assert response.status_code == 200
    assert '<html lang="ar" dir="rtl">' in response.text


def test_english_layout_remains_ltr(anonymous_client):
    response = anonymous_client.get("/login")

    assert response.status_code == 200
    assert '<html lang="en" dir="ltr">' in response.text


def test_authenticated_layout_exposes_direction(admin_client, monkeypatch):
    monkeypatch.setattr("enferno.app.get_locale", lambda: "ar")

    response = admin_client.get("/admin/labels/")

    assert response.status_code == 200
    assert '<html lang="ar" dir="rtl">' in response.text
