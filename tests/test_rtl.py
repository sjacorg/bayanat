from pathlib import Path


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


def test_all_first_party_drawers_use_logical_locations():
    roots = [
        Path("enferno/templates"),
        Path("enferno/admin/templates"),
        Path("enferno/data_import/templates"),
        Path("enferno/deduplication/templates"),
        Path("enferno/export/templates"),
    ]
    hardcoded_right = []

    for root in roots:
        for path in root.rglob("*.html"):
            source = path.read_text()
            if "<v-navigation-drawer" in source and 'location="right"' in source:
                hardcoded_right.append(str(path))

    assert hardcoded_right == []


def test_notification_payloads_detect_their_own_text_direction():
    source = Path("enferno/static/js/components/NotificationsList.js").read_text()

    assert source.count('dir="auto"') >= 2
    assert 'dir="ltr"' in source


def test_header_uses_logical_spacing():
    source = Path("enferno/admin/templates/nav-bar.html").read_text()
    logo = Path("enferno/static/img/bayanat-h-w-v2.svg").read_text()

    assert "ml-0" not in source
    assert "pl-2" not in source
    assert "mr-2" not in source
    assert "<v-toolbar-title" not in source
    assert source.index("bayanat-h-w-v2.svg") < source.index("</template>")
    assert 'viewBox="14 10 159 41"' in logo


def test_split_dialogs_use_logical_edges():
    bulletins = Path("enferno/admin/templates/admin/bulletins.html").read_text()
    events = Path("enferno/static/js/components/EventsSection.js").read_text()
    transcription = Path("enferno/static/js/components/MediaTranscriptionDialog.js").read_text()
    styles = Path("enferno/static/css/app.css").read_text()

    assert "'content-class': 'absolute inset-inline-start-0'" in bulletins
    assert "'content-class': 'absolute inset-inline-end-0'" in bulletins
    assert "position-fixed h-screen inset-inline-end-0 top-0 z-100" in events
    assert "position-absolute inset-inline-end-0 bottom-0" in transcription
    assert ".inset-inline-start-0" in styles
    assert ".inset-inline-end-0" in styles
    assert "'absolute left-0'" not in bulletins
    assert "'absolute right-0 left-auto'" not in bulletins


def test_map_drawer_and_controls_follow_text_direction():
    source = Path("enferno/static/js/components/MapVisualization.js").read_text()

    assert 'location="end"' in source
    assert 'location="right"' not in source
    assert "viewportPadding" in source
    assert "drawerToggleStyle" in source
    assert "drawerToggleIcon" in source
    assert ':viewport-padding="viewportPadding"' in source
