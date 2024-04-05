# database of operations ready to be processed for tax calculation 
from .Components import *
from sqlalchemy import String, Float, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


class Base(DeclarativeBase):
    pass

# ----------------------------------------------------
# ----------------- GenericOperation -----------------
# ----------------------------------------------------


class GenericOperation(Base):
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[String] = mapped_column(String)
    time: Mapped[DateTime] = mapped_column(DateTime)
    symbol: Mapped[String] = mapped_column(String(10), nullable=True)
    amount: Mapped[Float] = mapped_column(Float, nullable=True)
    sold_asset: Mapped[String] = mapped_column(String(10), nullable=True)
    sold_amount: Mapped[Float] = mapped_column(Float, nullable=True)
    bought_asset: Mapped[String] = mapped_column(String(10), nullable=True)
    bought_amount: Mapped[Float] = mapped_column(Float, nullable=True)
    fee_asset: Mapped[String] = mapped_column(String(10), nullable=True)
    fee_amount: Mapped[Float] = mapped_column(Float, nullable=True)

    def from_operation(operation: Operation):
        self = GenericOperation()
        self.type = operation.__class__.__name__
        self.time = operation.time
        if isinstance(operation, ExchangeOperation):
            self.symbol = operation.sold.symbol
            self.sold_asset = operation.sold.symbol
            self.sold_amount = operation.sold.amount
            self.bought_asset = operation.bought.symbol
            self.bought_amount = operation.bought.amount
            self.fee_asset = operation.fee.symbol
            self.fee_amount = operation.fee.amount
        elif isinstance(operation, OperationWithSymbolAmount):
            self.symbol = operation.asset.symbol
            self.amount = operation.asset.amount
        else:
            raise ValueError("Unknown operation type")
        return self

    def to_operation(self) -> Operation:
        if self.type == "ExchangeOperation":
            return ExchangeOperation(
                AssetAmount(self.sold_asset, self.sold_amount),
                AssetAmount(self.bought_asset, self.bought_amount),
                AssetAmount(self.fee_asset, self.fee_amount),
                self.time
            )
        elif self.type == "FeePayment":
            return FeePayment(self.symbol, self.amount, self.time)
        elif self.type == "Withdrawal":
            return Withdrawal(self.symbol, self.amount, self.time)
        else:
            # get the class from the name
            cls = globals()[self.type]
            return cls(self.symbol, self.amount, self.time)
            raise ValueError("Unknown operation type")


# ----------------------------------------------
# ----------------- ParsedFile -----------------
# ----------------------------------------------
class ParsedFile(Base):
    __tablename__ = "parsed_files"
    file: Mapped[str] = mapped_column(String(60), primary_key=True)
    last_line: Mapped[float] = mapped_column(Float)


# ------------------------------------------------------
# ----------------- OperationsDatabase -----------------
# ------------------------------------------------------
class OperationsDatabase:
    def __init__(self, db_file: str): 
        self.db_file = db_file
        self.engine = create_engine(f'sqlite:///{self.db_file}')
        self.session = Session(self.engine)
        self.cached_parsed_files = {}
        self.create_tables()

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def add_operations(self, operations: list[Operation]):
        for op in operations:
            self.session.add(GenericOperation.from_operation(op))

    def check_parsed(self, file: str, line: int) -> bool:
        last_line = self.get_last_line_parsed(file)
        return last_line >= line

    def get_last_line_parsed(self, file: str) -> int:
        if file in self.cached_parsed_files:
            return self.cached_parsed_files[file]

        with Session(self.engine) as session:
            result = session.execute(
                select(ParsedFile)
                .where(ParsedFile.file == file))
            finfo = result.scalar_one_or_none()
            if finfo is not None:
                self.cached_parsed_files[file] = finfo.last_line
            else:
                self.cached_parsed_files[file] = -1
        return self.cached_parsed_files[file]

    def set_parsed(self, file: str, last_line: int):
        fileInfo = self.session.execute(
            select(ParsedFile)
            .where(ParsedFile.file == file)).scalar_one_or_none()
        if fileInfo is not None:
            fileInfo.last_line = last_line
        else:
            self.session.add(ParsedFile(file=file, last_line=last_line))
            
    def get_operations(self) -> list[Operation]:
        with Session(self.engine) as session:
            result = session.execute(select(GenericOperation))
            return [op.to_operation() for op in result.scalars()]
    
    def save(self):
        self.cached_parsed_files = {}
        self.session.commit()
        self.session.close()
        self.session = Session(self.engine)
