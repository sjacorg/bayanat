from typing import List
import pytest
from pydantic import parse_obj_as

from tests.admin.test_atoa_infos import clean_slate_atoa_infos, create_atoa_info
from tests.admin.test_atob_infos import clean_slate_atob_infos, create_atob_info
from tests.admin.test_btob_infos import clean_slate_btob_infos, create_btob_info
from tests.admin.test_itoi_infos import clean_slate_itoi_infos, create_itoi_info
from tests.admin.test_itob_infos import clean_slate_itob_infos, create_itob_info
from tests.admin.test_itoa_infos import clean_slate_itoa_infos, create_itoa_info

from enferno.admin.models import AtobInfo, AtoaInfo, BtobInfo, ItoiInfo, ItobInfo, ItoaInfo

#### PYDANTIC MODELS #####

from tests.models.admin import (
    AtoaInfoItemModel,
    AtobInfoItemModel,
    BtobInfoItemModel,
    ItoiInfoItemModel,
    ItoaInfoItemModel,
    ItobInfoItemModel,
)
from tests.test_utils import convert_empty_strings_to_none, load_data


tables = [
    ("atob", "clean_slate_atob_infos", "create_atob_info", AtobInfoItemModel, AtobInfo),
    ("atoa", "clean_slate_atoa_infos", "create_atoa_info", AtoaInfoItemModel, AtoaInfo),
    ("btob", "clean_slate_btob_infos", "create_btob_info", BtobInfoItemModel, BtobInfo),
    ("itoi", "clean_slate_itoi_infos", "create_itoi_info", ItoiInfoItemModel, ItoiInfo),
    ("itob", "clean_slate_itob_infos", "create_itob_info", ItobInfoItemModel, ItobInfo),
    ("itoa", "clean_slate_itoa_infos", "create_itoa_info", ItoaInfoItemModel, ItoaInfo),
]

##### GET /admin/api/relation/info #####

relation_info_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", relation_info_endpoint_roles)
@pytest.mark.parametrize("table_name, clean_slate_fn, create_fn, item_model, model", tables)
def test_relation_info_endpoint(
    request,
    client_fixture,
    expected_status,
    table_name,
    clean_slate_fn,
    create_fn,
    item_model,
    model,
):
    clean = request.getfixturevalue(clean_slate_fn)
    create = request.getfixturevalue(create_fn)
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        f"/admin/api/relation/info?type={table_name}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        relations = parse_obj_as(
            List[item_model], convert_empty_strings_to_none(load_data(response))
        )
        assert len(relations) == len(model.query.all())
