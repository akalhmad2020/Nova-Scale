from app.core.database import SessionFactory
from app.modules.documents.application.use_cases.complete_shipment_label import (
    CompleteShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.create_document import (
    CreateDocumentUseCase,
)
from app.modules.documents.application.use_cases.create_shipment_label import (
    CreateShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.get_document import (
    GetDocumentUseCase,
)
from app.modules.documents.application.use_cases.get_shipment_label import (
    GetShipmentLabelUseCase,
)
from app.modules.documents.application.use_cases.list_shipment_documents import (
    ListShipmentDocumentsUseCase,
)
from app.modules.documents.application.use_cases.list_shipment_labels import (
    ListShipmentLabelsUseCase,
)
from app.modules.documents.application.use_cases.mark_document_failed import (
    MarkDocumentFailedUseCase,
)
from app.modules.documents.application.use_cases.mark_shipment_label_failed import (
    MarkShipmentLabelFailedUseCase,
)
from app.modules.documents.application.use_cases.void_shipment_label import (
    VoidShipmentLabelUseCase,
)
from app.modules.documents.infrastructure.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


def get_create_document_use_case() -> CreateDocumentUseCase:
    return CreateDocumentUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_document_use_case() -> GetDocumentUseCase:
    return GetDocumentUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_shipment_documents_use_case() -> ListShipmentDocumentsUseCase:
    return ListShipmentDocumentsUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_mark_document_failed_use_case() -> MarkDocumentFailedUseCase:
    return MarkDocumentFailedUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_create_shipment_label_use_case() -> CreateShipmentLabelUseCase:
    return CreateShipmentLabelUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_get_shipment_label_use_case() -> GetShipmentLabelUseCase:
    return GetShipmentLabelUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_list_shipment_labels_use_case() -> ListShipmentLabelsUseCase:
    return ListShipmentLabelsUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_complete_shipment_label_use_case() -> CompleteShipmentLabelUseCase:
    return CompleteShipmentLabelUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_void_shipment_label_use_case() -> VoidShipmentLabelUseCase:
    return VoidShipmentLabelUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )


def get_mark_shipment_label_failed_use_case() -> MarkShipmentLabelFailedUseCase:
    return MarkShipmentLabelFailedUseCase(
        unit_of_work=SQLAlchemyUnitOfWork(SessionFactory),
    )
