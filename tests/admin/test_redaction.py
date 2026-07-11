import io

import fitz
import pytest
from PIL import Image

from enferno.admin.models import Bulletin, Media
from enferno.utils.redaction_utils import RedactionError, redact_image_bytes, redact_pdf_bytes


def _one_page_pdf_with_text(text="SECRET NAME"):
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_text((10, 100), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def test_redact_pdf_removes_text_under_box():
    src = _one_page_pdf_with_text("SECRET NAME")
    pages = [{"page": 0, "rects": [{"x": 0.0, "y": 0.45, "w": 1.0, "h": 0.10}]}]

    out = redact_pdf_bytes(src, pages)

    doc = fitz.open(stream=out, filetype="pdf")
    remaining = doc[0].get_text()
    doc.close()
    assert "SECRET" not in remaining
    assert "NAME" not in remaining


def test_redact_pdf_blanks_image_pixels_not_whole_page():
    img = Image.new("RGB", (200, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    page.insert_image(page.rect, stream=buf.getvalue())
    src = doc.tobytes()
    doc.close()

    pages = [{"page": 0, "rects": [{"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}]}]
    out = redact_pdf_bytes(src, pages)

    doc = fitz.open(stream=out, filetype="pdf")
    pix = doc[0].get_pixmap()
    center = pix.pixel(100, 100)
    corner = pix.pixel(5, 5)
    doc.close()
    assert center == (0, 0, 0)
    assert corner == (255, 255, 255)


def test_redact_image_bytes_burns_black_box():
    img = Image.new("RGB", (100, 100), "white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    out = redact_image_bytes(buf.getvalue(), [{"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5}])

    result = Image.open(io.BytesIO(out)).convert("RGB")
    assert result.getpixel((10, 10)) == (0, 0, 0)
    assert result.getpixel((90, 90)) == (255, 255, 255)


def test_redact_image_bytes_honors_exif_orientation():
    # Raw pixels are landscape (200x100) but EXIF says rotate 90 CW, so the browser
    # (and the redaction UI) show it portrait (100x200). Boxes are drawn in that
    # displayed space, so the backend must transpose before burning.
    img = Image.new("RGB", (200, 100), "white")
    exif = img.getexif()
    exif[274] = 6  # Orientation: rotate 90 CW on display
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)

    out = redact_image_bytes(buf.getvalue(), [{"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5}])

    result = Image.open(io.BytesIO(out)).convert("RGB")
    assert result.size == (100, 200)  # displayed (transposed) dimensions, not raw
    assert result.getpixel((10, 10)) == (0, 0, 0)
    assert result.getpixel((90, 190)) == (255, 255, 255)


def test_redaction_rejects_out_of_bounds_coordinates():
    src = _one_page_pdf_with_text()
    pages = [{"page": 0, "rects": [{"x": -0.1, "y": 0, "w": 0.2, "h": 0.2}]}]

    with pytest.raises(RedactionError):
        redact_pdf_bytes(src, pages)


def test_redact_endpoint_creates_new_media_and_audit_row(admin_client, session):
    from enferno.admin.models import MediaRedaction

    src = _one_page_pdf_with_text("SECRET NAME")
    filename = Media.generate_file_name("source.pdf")
    path = Media.media_dir / filename
    path.write_bytes(src)

    bulletin = Bulletin(title="Redaction test")
    session.add(bulletin)
    session.flush()
    media = Media(
        media_file=filename,
        media_file_type="application/pdf",
        etag="source-etag",
        title="Source document",
        bulletin_id=bulletin.id,
    )
    session.add(media)
    session.commit()
    media_id = media.id
    redacted = None

    try:
        resp = admin_client.post(
            f"/admin/api/media/{media_id}/redact",
            json={"pages": [{"page": 0, "rects": [{"x": 0, "y": 0.45, "w": 1, "h": 0.1}]}]},
        )

        assert resp.status_code == 200
        redacted = resp.get_json()["data"]
        assert redacted["id"] != media_id
        assert redacted["title"] == "Source document (redacted)"
        audit = MediaRedaction.query.filter_by(
            source_media_id=media_id,
            result_media_id=redacted["id"],
        ).one()
        assert audit.user_id is not None
    finally:
        MediaRedaction.query.filter_by(source_media_id=media_id).delete()
        session.commit()
        path.unlink(missing_ok=True)
        if redacted:
            (Media.media_dir / redacted["filename"]).unlink(missing_ok=True)


def test_delete_endpoint_soft_deletes_redacted_copy_only(admin_client, session):
    from enferno.admin.models import MediaRedaction

    bulletin = Bulletin(title="Soft-delete test")
    session.add(bulletin)
    session.flush()
    original = Media(
        media_file="orig.pdf",
        media_file_type="application/pdf",
        etag="orig",
        bulletin_id=bulletin.id,
    )
    redacted = Media(
        media_file="red.pdf", media_file_type="application/pdf", etag="red", bulletin_id=bulletin.id
    )
    session.add_all([original, redacted])
    session.flush()
    audit = MediaRedaction(
        source_media_id=original.id,
        original_media_id=original.id,
        result_media_id=redacted.id,
        regions=[],
    )
    session.add(audit)
    session.commit()
    original_id, redacted_id = original.id, redacted.id

    try:
        # Original (no redaction backref) is rejected.
        resp = admin_client.delete(f"/admin/api/media/{original_id}/redact")
        assert resp.status_code == 400
        assert Media.query.get(original_id).deleted is False

        # Redacted copy is soft-deleted: hidden from normal queries, still
        # reachable via the include_deleted opt-out with deleted set.
        resp = admin_client.delete(f"/admin/api/media/{redacted_id}/redact")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"id": redacted_id, "deleted": True}
        assert Media.query.get(redacted_id) is None
        row = Media.query.execution_options(include_deleted=True).get(redacted_id)
        assert row.deleted is True
    finally:
        MediaRedaction.query.filter_by(source_media_id=original_id).delete()
        Media.query.filter(Media.id.in_([original_id, redacted_id])).delete(
            synchronize_session=False
        )
        session.commit()


def test_bulletin_to_dict_excludes_deleted_media(session):
    bulletin = Bulletin(title="Deleted media exclusion")
    session.add(bulletin)
    session.flush()
    live = Media(
        media_file="live.pdf",
        media_file_type="application/pdf",
        etag="live",
        bulletin_id=bulletin.id,
    )
    gone = Media(
        media_file="gone.pdf",
        media_file_type="application/pdf",
        etag="gone",
        bulletin_id=bulletin.id,
        deleted=True,
    )
    session.add_all([live, gone])
    session.commit()
    live_id, gone_id = live.id, gone.id

    try:
        media_ids = {m["id"] for m in bulletin.to_dict()["medias"]}
        assert live_id in media_ids
        assert gone_id not in media_ids
    finally:
        Media.query.filter(Media.id.in_([live_id, gone_id])).delete(synchronize_session=False)
        session.commit()


def test_media_dashboard_excludes_deleted(admin_client, session):
    bulletin = Bulletin(title="Dashboard exclusion")
    session.add(bulletin)
    session.flush()
    live = Media(
        media_file="dlive.pdf",
        media_file_type="application/pdf",
        etag="dlive",
        bulletin_id=bulletin.id,
    )
    gone = Media(
        media_file="dgone.pdf",
        media_file_type="application/pdf",
        etag="dgone",
        bulletin_id=bulletin.id,
        deleted=True,
    )
    session.add_all([live, gone])
    session.commit()
    live_id, gone_id = live.id, gone.id

    try:
        resp = admin_client.get(f"/admin/api/media/dashboard?bulletin_id={bulletin.id}")
        assert resp.status_code == 200
        ids = {m["id"] for m in resp.get_json()["items"]}
        assert live_id in ids
        assert gone_id not in ids
    finally:
        Media.query.filter(Media.id.in_([live_id, gone_id])).delete(synchronize_session=False)
        session.commit()
