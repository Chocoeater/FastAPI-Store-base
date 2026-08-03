from datetime import datetime

from sqlalchemy import ForeignKey, Text, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    __table_args__ = (
        CheckConstraint('grade >= 1 AND grade <= 5', name='check_grade_range'),
    )

    id: Mapped[int] = mapped_column( primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id'))
    comment: Mapped[str | None] = mapped_column(Text)
    comment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    grade: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship("User", back_populates="reviews")
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")