from typing import Any

from sqlalchemy.orm import Session

from app.models.idempotency_record import IdempotencyRecord


class IdempotencyRepository:
    def get(
        self, db: Session, *, family_id: int, operation: str, key: str
    ) -> IdempotencyRecord | None:
        """
        在家庭和操作作用域内读取幂等记录。
        """
        return (
            db.query(IdempotencyRecord)
            .filter(
                IdempotencyRecord.family_id == family_id,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.key == key,
            )
            .first()
        )

    def create(
        self,
        db: Session,
        *,
        family_id: int,
        operation: str,
        key: str,
        status_code: int,
        response_body: dict[str, Any],
    ) -> IdempotencyRecord:
        """
        保存已成功处理的幂等请求结果。
        """
        db_obj = IdempotencyRecord(
            family_id=family_id,
            operation=operation,
            key=key,
            status_code=status_code,
            response_body=response_body,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


idempotency_repo = IdempotencyRepository()
