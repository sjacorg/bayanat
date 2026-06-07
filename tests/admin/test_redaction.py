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
