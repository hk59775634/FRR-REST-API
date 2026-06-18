"""向后兼容：旧模块 re-export。"""
from app.services import isis, ospf, ospf6, rip, ripng
from app.services.isis import get_instance as get_isis_instance
from app.services.isis import get_neighbors as get_isis_neighbors
from app.services.isis import get_summary as get_isis_summary
from app.services.ospf import get_instance as get_ospf_instance
from app.services.ospf import get_neighbors as get_ospf_neighbors
from app.services.ospf import get_summary as get_ospf_summary
from app.services.ospf6 import get_instance as get_ospf6_instance
from app.services.ospf6 import get_summary as get_ospf6_summary
from app.services.rip import get_instance as get_rip_instance
from app.services.rip import get_status as get_rip_status
from app.services.ripng import get_instance as get_ripng_instance
from app.services.ripng import get_status as get_ripng_status
