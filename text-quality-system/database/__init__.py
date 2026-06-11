# database package
from .db import (
    init_db,
    save_result,
    get_all,
    get_by_id,
    delete_by_id,
    get_ranking,
    clear_all,
)
from .models import TextRecord
