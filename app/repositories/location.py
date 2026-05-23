from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate

class LocationRepository(BaseRepository[Location, LocationCreate, LocationUpdate]):
    def get_by_family(self, db: Session, *, family_id: int, parent_id: Optional[int] = None) -> List[Location]:
        """
        获取家庭空间列表，可按父节点过滤
        """
        query = db.query(self.model).filter(
            self.model.family_id == family_id,
            self.model.parent_id == parent_id
        )
        return query.all()

    def get_all_family_locations(self, db: Session, *, family_id: int) -> List[Location]:
        """
        获取家庭的全部空间记录
        """
        return db.query(self.model).filter(self.model.family_id == family_id).all()

    def get_descendant_ids(self, db: Session, *, location_id: int) -> List[int]:
        """
        使用 SQLAlchemy CTE 递归查询获取某个空间的所有子孙空间 ID
        """
        # 1. 基础部分：当前起点空间
        base_query = select(self.model.id).where(self.model.id == location_id)

        # 2. 递归声明 CTE
        cte_query = base_query.cte(name="descendants", recursive=True)

        # 3. 递归部分：联合查询子节点
        recursive_part = select(self.model.id).join(
            cte_query,
            self.model.parent_id == cte_query.c.id
        )

        # 4. 合并并运行
        recursive_cte = cte_query.union_all(recursive_part)

        # 5. 执行查询并返回 ID 列表
        results = db.execute(select(recursive_cte.c.id)).all()
        return [r[0] for r in results]

    def get_ancestor_path(self, db: Session, *, location_id: int) -> List[dict]:
        """
        使用 SQLAlchemy CTE 递归查询获取从根节点到当前节点路径的面包屑列表
        """
        # 1. 基础部分：当前节点
        base_query = select(self.model.id, self.model.name, self.model.parent_id).where(self.model.id == location_id)

        # 2. 递归声明 CTE
        cte_query = base_query.cte(name="ancestors", recursive=True)

        # 3. 递归部分：向上联合查询父节点
        recursive_part = select(self.model.id, self.model.name, self.model.parent_id).join(
            cte_query,
            self.model.id == cte_query.c.parent_id
        )

        # 4. 合并并运行
        recursive_cte = cte_query.union_all(recursive_part)

        # 5. 执行查询
        results = db.execute(select(recursive_cte.c.id, recursive_cte.c.name)).all()

        # 6. 将结果从底向上还原，我们需要反转它以得到“从根节点到叶节点”的顺序
        path = [{"id": r[0], "name": r[1]} for r in results]
        path.reverse()
        return path

    def create_in_family(self, db: Session, *, obj_in: LocationCreate, family_id: int) -> Location:
        """
        在指定家庭创建空间
        """
        db_obj = Location(
            name=obj_in.name,
            parent_id=obj_in.parent_id,
            family_id=family_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

location_repo = LocationRepository(Location)
