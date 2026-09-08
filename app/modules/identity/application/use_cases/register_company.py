from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.modules.identity.application.exceptions import (
    EmailAlreadyRegisteredError,
    TenantSlugAlreadyExistsError,
)
from app.modules.identity.application.ports.password_hasher import PasswordHasher
from app.modules.identity.application.ports.unit_of_work import UnitOfWork
from app.modules.identity.domain.enums import MembershipStatus, TenantStatus
from app.modules.identity.infrastructure.models.membership import Membership
from app.modules.identity.infrastructure.models.tenant import Tenant
from app.modules.identity.infrastructure.models.user import User
from app.modules.ledger.application.use_cases.bootstrap_accounts import (
    SYSTEM_LEDGER_ACCOUNTS,
)
from app.modules.ledger.domain.enums import LedgerAccountStatus
from app.modules.ledger.infrastructure.models import LedgerAccount
from app.modules.saas.domain.enums import PlanCode, SubscriptionStatus
from app.modules.saas.infrastructure.models.subscription import TenantSubscription


@dataclass(frozen=True, slots=True)
class RegisterCompanyCommand:
    email: str
    password: str
    first_name: str
    last_name: str
    company_name: str
    company_slug: str


@dataclass(frozen=True, slots=True)
class RegisterCompanyResult:
    user_id: UUID
    tenant_id: UUID
    membership_id: UUID
    email: str
    first_name: str
    last_name: str
    company_name: str
    company_slug: str


class RegisterCompany:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    async def execute(
        self,
        command: RegisterCompanyCommand,
    ) -> RegisterCompanyResult:
        email = command.email.strip().lower()
        company_name = command.company_name.strip()
        company_slug = command.company_slug.strip().lower()

        async with self._unit_of_work as uow:
            if await uow.users.email_exists(email):
                raise EmailAlreadyRegisteredError

            if await uow.tenants.get_by_slug(company_slug) is not None:
                raise TenantSlugAlreadyExistsError

            owner_role = await uow.roles.get_by_name("owner")

            if owner_role is None:
                raise RuntimeError("Owner role is not configured")

            user = User(
                email=email,
                password_hash=self._password_hasher.hash(command.password),
                first_name=command.first_name.strip(),
                last_name=command.last_name.strip(),
            )
            uow.users.add(user)

            tenant = Tenant(
                name=company_name,
                slug=company_slug,
                status=TenantStatus.ACTIVE,
            )
            uow.tenants.add(tenant)

            try:
                await uow.flush()
            except IntegrityError as exc:
                await uow.rollback()
                raise self._translate_integrity_error(exc) from exc

            membership = Membership(
                tenant_id=tenant.id,
                user_id=user.id,
                role_id=owner_role.id,
                status=MembershipStatus.ACTIVE,
            )
            uow.memberships.add(membership)

            subscription = TenantSubscription(
                tenant_id=tenant.id,
                plan_code=PlanCode.STARTER,
                status=SubscriptionStatus.ACTIVE,
            )
            uow.subscriptions.add(subscription)

            for definition in SYSTEM_LEDGER_ACCOUNTS:
                account = LedgerAccount(
                    tenant_id=tenant.id,
                    code=definition.code,
                    name=definition.name,
                    type=definition.type.value,
                    purpose=definition.purpose.value,
                    status=LedgerAccountStatus.ACTIVE.value,
                )
                await uow.ledger_accounts.add(account)

            try:
                await uow.flush()
            except IntegrityError as exc:
                await uow.rollback()
                raise self._translate_integrity_error(exc) from exc

            await uow.commit()

            return RegisterCompanyResult(
                user_id=user.id,
                tenant_id=tenant.id,
                membership_id=membership.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                company_name=tenant.name,
                company_slug=tenant.slug,
            )

    @staticmethod
    def _translate_integrity_error(
        exc: IntegrityError,
    ) -> Exception:
        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name is None:
            cause = getattr(exc.orig, "__cause__", None)

            constraint_name = getattr(
                cause,
                "constraint_name",
                None,
            )

        if constraint_name == "uq_users_email":
            return EmailAlreadyRegisteredError()

        if constraint_name == "uq_tenants_slug":
            return TenantSlugAlreadyExistsError()

        return exc
