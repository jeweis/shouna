from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.repositories.location import location_repo
from app.models.location import Location
from app.models.item import Item
from app.schemas.location import LocationCreate, LocationUpdate, LocationTreeNode

class LocationService:
    def create_location(self, db: Session, *, obj_in: LocationCreate, family_id: int) -> Location:
        """
        在当前家庭下创建空间，包含父空间合法性及循环嵌套校验
        """
        if obj_in.parent_id:
            # 1. 验证父空间是否存在，且属于同一个家庭
            parent = location_repo.get(db, id=obj_in.parent_id)
            if not parent:
                raise ValueError("父空间不存在")
            if parent.family_id != family_id:
                raise ValueError("越权访问：父空间不属于该家庭")

        return location_repo.create_in_family(db, obj_in=obj_in, family_id=family_id)

    def update_location(
        self, db: Session, *, location_id: int, obj_in: LocationUpdate, family_id: int
    ) -> Location:
        """
        更新空间信息，包含循环引用安全校验
        """
        db_obj = location_repo.get(db, id=location_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("空间不存在或越权访问")

        # 如果变更了 parent_id，进行防循环嵌套校验
        if obj_in.parent_id is not None:
            if obj_in.parent_id == location_id:
                raise ValueError("空间不能成为其自身的子空间")

            # 验证新父空间是否在该家庭中
            new_parent = location_repo.get(db, id=obj_in.parent_id)
            if not new_parent or new_parent.family_id != family_id:
                raise ValueError("新父空间不存在或越权访问")

            # 递归查询当前空间的所有子孙 ID，防止新父节点成为其自身的后代
            descendants = location_repo.get_descendant_ids(db, location_id=location_id)
            if obj_in.parent_id in descendants:
                raise ValueError("不能将空间移动到其自身的子空间下（形成循环引用）")

        return location_repo.update(db, db_obj=db_obj, obj_in=obj_in)

    def delete_location(self, db: Session, *, location_id: int, family_id: int) -> Location:
        """
        级联删除空间（由于模型配了 cascade="all, delete-orphan"，SQLAlchemy/SQLite 会自动处理后代及物品）
        """
        db_obj = location_repo.get(db, id=location_id)
        if not db_obj or db_obj.family_id != family_id:
            raise ValueError("空间不存在或越权访问")

        return location_repo.remove(db, id=location_id)

    def get_location_tree(self, db: Session, *, family_id: int) -> List[LocationTreeNode]:
        """
        获取该家庭的完整空间树结构，携带各个空间及其子空间的物品数量
        """
        all_locations = location_repo.get_all_family_locations(db, family_id=family_id)
        direct_item_counts = self._get_direct_item_counts(db, family_id=family_id)

        nodes: Dict[int, LocationTreeNode] = {}
        children_by_parent: Dict[int, List[Location]] = {}
        for loc in all_locations:
            if loc.parent_id is not None:
                children_by_parent.setdefault(loc.parent_id, []).append(loc)
            nodes[loc.id] = LocationTreeNode(
                id=loc.id,
                name=loc.name,
                parent_id=loc.parent_id,
                family_id=loc.family_id,
                created_at=loc.created_at,
                item_count=0,
                sub_locations=[]
            )

        for loc in all_locations:
            nodes[loc.id].item_count = self._count_subtree_items(
                loc,
                children_by_parent=children_by_parent,
                direct_item_counts=direct_item_counts,
            )

        roots: List[LocationTreeNode] = []
        for loc in all_locations:
            node = nodes[loc.id]
            if loc.parent_id is None:
                roots.append(node)
            else:
                parent_node = nodes.get(loc.parent_id)
                if parent_node:
                    parent_node.sub_locations.append(node)

        return roots

    def _get_direct_item_counts(self, db: Session, *, family_id: int) -> Dict[int, int]:
        rows = db.query(Item.location_id, Item.id).filter(Item.family_id == family_id).all()
        counts: Dict[int, int] = {}
        for location_id, _ in rows:
            counts[location_id] = counts.get(location_id, 0) + 1
        return counts

    def _count_subtree_items(
        self,
        location: Location,
        *,
        children_by_parent: Dict[int, List[Location]],
        direct_item_counts: Dict[int, int],
    ) -> int:
        total = direct_item_counts.get(location.id, 0)
        for child in children_by_parent.get(location.id, []):
            total += self._count_subtree_items(
                child,
                children_by_parent=children_by_parent,
                direct_item_counts=direct_item_counts,
            )
        return total

location_service = LocationService()
